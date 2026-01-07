import logging
import yaml
from typing import Any, cast, Literal
from datetime import datetime
from rich import print as rprint

from acp import (
    PROTOCOL_VERSION,
    Agent,
    AuthenticateResponse,
    InitializeResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptResponse,
    SetSessionModeResponse,
    update_agent_message_text,
    update_agent_thought_text,
    update_tool_call,
    start_tool_call,
    run_agent,
)
from acp.interfaces import Client
from acp.schema import (
    AgentCapabilities,
    ForkSessionResponse,
    ListSessionsResponse,
    PromptCapabilities,
    McpCapabilities,
    AudioContentBlock,
    ClientCapabilities,
    EmbeddedResourceContentBlock,
    HttpMcpServer,
    ImageContentBlock,
    Implementation,
    McpServerStdio,
    ResourceContentBlock,
    ResumeSessionResponse,
    SetSessionModelResponse,
    SseMcpServer,
    TextContentBlock,
    SessionModeState,
    SessionInfo,
)

from .workflow import AgentWorkflow
from .llm_wrapper import LLMWrapper
from .models import Tool
from .tools import TOOLS, DefaultToolType, filter_tools, AGENTFS_TOOLS
from .tools.agentfs import load_all_files
from .events import (
    InputEvent,
    OutputEvent,
    ThinkingEvent,
    PromptEvent,
    PermissionResponseEvent,
    ToolPermissionEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from .mcp_wrapper import McpWrapper, McpServersConfig
from .constants import (
    MODES,
    PERMISSION_OPTIONS,
    AGENT_CONFIG_FILE,
    VERSION,
    DEFAULT_MODE_ID,
    MCP_CONFIG_FILE,
    AGENTFS_FILE,
    AVAILABLE_MODELS,
    DEFAULT_GOOGLE_MODEL,
)


class AcpAgentWorkflow(Agent):
    """
    Implementation of the Agent for the ACP protocol, allowing LlamaIndex Workflows to communicate through it.

    Attributes:
        _conn (Client): ACP Client-side connection
        _next_session_id (int): ID for the incoming session request
        _session_infos (dict[str, SessionInfo]): dictionary mapping session IDs with session metadata
        _sessions (set[str]): set of all the sessions created during the agent's lifespan
        _current_tool_call_id (int): ID tracking the number of tool calls.
        _llm (LLMWrapper): LLM to use with the LlamaIndex Workflow
        _mcp_client (McpWrapper | None): MCP client to use with the LlamaIndex Workflow. None if MCP use is not requested.
    """

    _conn: Client

    def __init__(
        self,
        llm_model: str | None = None,
        agent_task: str | None = None,
        tools: list[Tool] | list[DefaultToolType] | None = None,
        mode: str | None = None,
        mcp_wrapper: McpWrapper | None = None,
        mcp_tools: list[Tool] | None = None,
        use_agentfs: bool = False,
    ) -> None:
        """
        Initialize the AcpAgentWorkflow instance.

        Args:
            llm_model (str | None): LLM model to use.
            agent_task (str | None): Task description for the agent.
            tools (list[Tool] | list[DefaultToolType] | None): List of tools to use.
            mode (str | None): Mode identifier.
            mcp_wrapper (McpWrapper | None): MCP client wrapper.
            mcp_tools (list[Tool] | None): Additional MCP tools.
        """
        self._next_session_id = 0
        self._sessions: set[str] = set()
        self._session_infos: dict[str, SessionInfo] = {}
        self._mode: str = mode or DEFAULT_MODE_ID
        self._current_tool_call_id: int = 0
        _impl_tools: list[Tool] = TOOLS if not use_agentfs else AGENTFS_TOOLS
        if tools is not None:
            first_item = next(iter(tools))
            if isinstance(first_item, Tool):
                _impl_tools = cast(list[Tool], tools)
            else:
                _impl_tools = filter_tools(
                    names=cast(list[DefaultToolType], tools), use_agentfs=use_agentfs
                )
        if mcp_tools is not None:
            _impl_tools.extend(mcp_tools)
        llm_model = llm_model or DEFAULT_GOOGLE_MODEL
        self._llm = LLMWrapper(
            tools=_impl_tools,
            agent_task=agent_task,
            model=llm_model,
            llm_provider=AVAILABLE_MODELS[llm_model],
        )
        self._mcp_client = mcp_wrapper

    @classmethod
    def ext_from_config_file(
        cls,
        mcp_wrapper: McpWrapper | None = None,
        mcp_tools: list[Tool] | None = None,
        use_agentfs: bool = False,
    ) -> "AcpAgentWorkflow":
        """
        Create an AcpAgentWorkflow instance from a config file.

        Args:
            mcp_wrapper (McpWrapper | None): MCP client wrapper.
            mcp_tools (list[Tool] | None): Additional MCP tools.
        Returns:
            AcpAgentWorkflow: The initialized agent workflow.
        """
        assert AGENT_CONFIG_FILE.exists() and AGENT_CONFIG_FILE.is_file(), (
            f"No such file: {str(AGENT_CONFIG_FILE)}"
        )
        with open(AGENT_CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f)
        config: dict[str, Any] = {
            "agent_task": None,
            "llm_model": None,
            "tools": None,
            "mode": None,
            "mcp_wrapper": mcp_wrapper,
            "mcp_tools": mcp_tools,
            "use_agentfs": use_agentfs,
        }
        if "agent_task" in data:
            config["agent_task"] = data["agent_task"]
        if "model" in data:
            if data["model"] not in AVAILABLE_MODELS:
                raise ValueError(
                    f"Cannot use {data['model']} as LLM model. Choose one among: {', '.join(list(AVAILABLE_MODELS.keys()))}"
                )
            config["llm_model"] = data["model"]
        if "tools" in data:
            assert isinstance(data["tools"], list)
            config["tools"] = cast(list[DefaultToolType], data["tools"])
        if "mode" in data:
            config["mode"] = data["mode"]
        return cls(**config)

    def _get_tool_call_id(self, increment: bool = True) -> str:
        """
        Generate or retrieve the current tool call ID.

        Args:
            increment (bool): Whether to increment the call ID.
        Returns:
            str: The tool call ID string.
        """
        if increment:
            self._current_tool_call_id += 1
            return f"call_{self._current_tool_call_id}"
        else:
            return f"call_{self._current_tool_call_id}"

    def on_connect(self, conn: Client) -> None:
        """
        Set the ACP client connection for the agent.

        Args:
            conn (Client): The ACP client connection.
        """
        self._conn = conn

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: ClientCapabilities | None = None,
        client_info: Implementation | None = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        """
        Handle the initialize request from the client.

        Args:
            protocol_version (int): Protocol version.
            client_capabilities (ClientCapabilities | None): Client capabilities.
            client_info (Implementation | None): Client implementation info.
        Returns:
            InitializeResponse: The initialization response.
        """
        logging.info("Received initialize request")
        return InitializeResponse(
            protocol_version=PROTOCOL_VERSION,
            agent_capabilities=AgentCapabilities(
                prompt_capabilities=PromptCapabilities(
                    image=False, audio=False, embedded_context=False
                ),
                mcp_capabilities=McpCapabilities(http=False, sse=False),
            ),
            agent_info=Implementation(
                name="workflows-acp", title="AgentWorkflow", version=VERSION
            ),
        )

    async def authenticate(
        self, method_id: str, **kwargs: Any
    ) -> AuthenticateResponse | None:
        """
        Handle the authenticate request from the client.

        Args:
            method_id (str): Authentication method identifier.
        Returns:
            AuthenticateResponse | None: The authentication response.
        """
        logging.info("Received authenticate request %s", method_id)
        return AuthenticateResponse()

    async def new_session(
        self,
        cwd: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio],
        **kwargs: Any,
    ) -> NewSessionResponse:
        """
        Handle the new session request from the client.

        Args:
            cwd (str): Current working directory.
            mcp_servers (list): List of MCP servers.
        Returns:
            NewSessionResponse: The new session response.
        """
        logging.info("Received new session request")
        session_id = str(self._next_session_id)
        self._next_session_id += 1
        self._sessions.add(session_id)
        self._session_infos[session_id] = SessionInfo(
            cwd=cwd,
            title=f"Session {session_id}",
            session_id=session_id,
            updated_at=datetime.now().isoformat(),
        )
        return NewSessionResponse(
            session_id=session_id,
            modes=SessionModeState(available_modes=MODES, current_mode_id=self._mode),
        )

    async def load_session(
        self,
        cwd: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio],
        session_id: str,
        **kwargs: Any,
    ) -> LoadSessionResponse | None:
        """
        Handle the load session request from the client.

        Args:
            cwd (str): Current working directory.
            mcp_servers (list): List of MCP servers.
            session_id (str): Session identifier.
        Returns:
            LoadSessionResponse | None: The load session response.
        """
        logging.info("Received load session request %s", session_id)
        self._sessions.add(session_id)
        self._session_infos[session_id] = SessionInfo(
            cwd=cwd,
            title=f"Session {session_id}",
            session_id=session_id,
            updated_at=datetime.now().isoformat(),
        )
        return LoadSessionResponse(
            modes=SessionModeState(available_modes=MODES, current_mode_id=self._mode)
        )

    async def set_session_mode(
        self, mode_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModeResponse | None:
        """
        Set the session mode for a given session.

        Args:
            mode_id (str): Mode identifier.
            session_id (str): Session identifier.
        Returns:
            SetSessionModeResponse | None: The set session mode response.
        """
        logging.info("Received set session mode request %s -> %s", session_id, mode_id)
        self._mode = mode_id
        return SetSessionModeResponse()

    async def list_sessions(
        self, cursor: str | None = None, cwd: str | None = None, **kwargs: Any
    ) -> ListSessionsResponse:
        """
        List all sessions managed by the agent.

        Args:
            cursor (str | None): Optional cursor for pagination.
            cwd (str | None): Optional working directory.
        Returns:
            ListSessionsResponse: The list of sessions response.
        """
        return ListSessionsResponse(sessions=list(self._session_infos.values()))

    async def set_session_model(
        self, model_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModelResponse | None:
        """
        Set the model for a given session.

        Args:
            model_id (str): Model identifier.
            session_id (str): Session identifier.
        Returns:
            SetSessionModelResponse | None: The set session model response.
        """
        logging.info(
            "Received set session model request %s -> %s", session_id, model_id
        )
        return SetSessionModelResponse()

    async def fork_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio] | None = None,
        **kwargs: Any,
    ) -> ForkSessionResponse:
        """
        Fork an existing session.

        Args:
            cwd (str): Current working directory.
            session_id (str): Session identifier.
            mcp_servers (list | None): List of MCP servers.
        Returns:
            ForkSessionResponse: The fork session response.
        """
        logging.info("Received fork session request for %s", session_id)
        return ForkSessionResponse(
            session_id=session_id,
            modes=SessionModeState(available_modes=MODES, current_mode_id=self._mode),
        )

    async def resume_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio] | None = None,
        **kwargs: Any,
    ) -> ResumeSessionResponse:
        """
        Resume a previously existing session.

        Args:
            cwd (str): Current working directory.
            session_id (str): Session identifier.
            mcp_servers (list | None): List of MCP servers.
        Returns:
            ResumeSessionResponse: The resume session response.
        """
        logging.info("Received resume session request for %s", session_id)
        return ResumeSessionResponse(
            modes=SessionModeState(available_modes=MODES, current_mode_id=self._mode)
        )

    async def prompt(
        self,
        prompt: list[
            TextContentBlock
            | ImageContentBlock
            | AudioContentBlock
            | ResourceContentBlock
            | EmbeddedResourceContentBlock
        ],
        session_id: str,
        **kwargs: Any,
    ) -> PromptResponse:
        """
        Handle a prompt request from the client, streaming events and updating session state.

        Args:
            prompt (list): List of content blocks for the prompt.
            session_id (str): Session identifier.
        Returns:
            PromptResponse: The prompt response.
        """
        logging.info("Received prompt request for session %s", session_id)
        if session_id not in self._sessions:
            self._sessions.add(session_id)
        _impl_prompt = ""
        for block in prompt:
            if isinstance(block, TextContentBlock):
                _impl_prompt += block.text + "\n"
        wf = AgentWorkflow(llm=self._llm, mcp_client=self._mcp_client)
        handler = wf.run(
            start_event=InputEvent(
                prompt=_impl_prompt, mode=cast(Literal["ask", "bypass"], self._mode)
            )
        )
        async for event in handler.stream_events():
            if isinstance(event, ThinkingEvent):
                await self._conn.session_update(
                    session_id=session_id,
                    update=update_agent_thought_text(event.content),
                )
            elif isinstance(event, PromptEvent):
                await self._conn.session_update(
                    session_id=session_id,
                    update=update_agent_message_text(event.prompt),
                )
            elif isinstance(event, ToolCallEvent):
                tool_title = f"Calling tool {event.tool_name}"
                await self._conn.session_update(
                    session_id=session_id,
                    update=start_tool_call(
                        tool_call_id=self._get_tool_call_id(),
                        title=tool_title,
                        status="pending",
                        raw_input=event.tool_input,
                    ),
                )
            elif isinstance(event, ToolResultEvent):
                tool_title = f"Result for tool {event.tool_name}"
                await self._conn.session_update(
                    session_id=session_id,
                    update=update_tool_call(
                        tool_call_id=self._get_tool_call_id(increment=False),
                        title=tool_title,
                        status="completed",
                        raw_output=event.result,
                    ),
                )
            elif isinstance(event, ToolPermissionEvent):
                tool_title = f"Calling tool {event.tool_name}"
                tc = update_tool_call(
                    tool_call_id=self._get_tool_call_id(increment=False),
                    title=tool_title,
                    status="in_progress",
                    raw_input=event.tool_input,
                )
                permres = await self._conn.request_permission(
                    options=PERMISSION_OPTIONS, session_id=session_id, tool_call=tc
                )
                if permres.outcome.outcome == "selected":
                    if permres.outcome.option_id == "allow":
                        handler.ctx.send_event(
                            PermissionResponseEvent(
                                allow=True,
                                reason=None,
                                tool_name=event.tool_name,
                                tool_input=event.tool_input,
                            )
                        )
                    else:
                        handler.ctx.send_event(
                            PermissionResponseEvent(
                                allow=False,
                                reason="You should not use this tool now, please come up with another plan",
                                tool_name=event.tool_name,
                                tool_input=event.tool_input,
                            )
                        )
                        await self._conn.session_update(
                            session_id=session_id,
                            update=update_tool_call(
                                tool_call_id=self._get_tool_call_id(increment=False),
                                title=tool_title,
                                status="failed",
                                raw_input=event.tool_input,
                            ),
                        )
                else:
                    handler.ctx.send_event(
                        PermissionResponseEvent(
                            allow=False,
                            reason="I want to cancel this tool call",
                            tool_name=event.tool_name,
                            tool_input=event.tool_input,
                        )
                    )
                    await self._conn.session_update(
                        session_id=session_id,
                        update=update_tool_call(
                            tool_call_id=self._get_tool_call_id(increment=False),
                            title=tool_title,
                            status="failed",
                            raw_input=event.tool_input,
                        ),
                    )
        result = await handler
        assert isinstance(result, OutputEvent)
        if result.error is None:
            message = f"I think that my run is complete because of the following reason: {result.stop_reason}\nThis is the final result for my task: {result.final_output}"
        else:
            message = f"An error occurred: {result.error}"
        await self._conn.session_update(
            session_id=session_id, update=update_agent_message_text(message)
        )
        return PromptResponse(stop_reason="end_turn")

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        """
        Handle a cancel notification for a session.

        Args:
            session_id (str): Session identifier.
        """
        logging.info("Received cancel notification for session %s", session_id)

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an external method call (not supported).

        Args:
            method (str): Method name.
            params (dict): Method parameters.
        Returns:
            dict[str, Any]: Error response.
        """
        logging.info("Received extension method call: %s", method)
        return {"error": "External methods not supported"}

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        """
        Handle an external notification (not supported).

        Args:
            method (str): Notification name.
            params (dict): Notification parameters.
        """
        logging.info("Received extension notification: %s", method)


async def _create_agent(
    llm_model: str | None = None,
    agent_task: str | None = None,
    tools: list[Tool] | list[DefaultToolType] | None = None,
    mode: str | None = None,
    from_config_file: bool = False,
    mcp_config: McpServersConfig | None = None,
    use_mcp: bool = True,
    use_agentfs: bool = False,
    agentfs_skip_files: list[str] | None = None,
    agentfs_skip_dirs: list[str] | None = None,
) -> AcpAgentWorkflow:
    """
    Create and configure an AcpAgentWorkflow instance.

    Args:
        llm_model (str | None): LLM model to use.
        agent_task (str | None): Task description for the agent.
        tools (list[Tool] | list[DefaultToolType] | None): List of tools to use.
        mode (str | None): Mode identifier.
        from_config_file (bool): Whether to load from config file.
        mcp_config (McpServersConfig | None): MCP configuration.
        use_mcp (bool): Whether to use MCP.
    Returns:
        AcpAgentWorkflow: The configured agent workflow instance.
    """
    if use_agentfs:
        if not AGENTFS_FILE.exists():
            logging.info(
                "Loading all files in the current working directory to AgentFS"
            )
            await load_all_files(agentfs_skip_dirs, agentfs_skip_files)
            logging.info(
                "Finished loading all files in the current working directory to AgentFS"
            )
        else:
            logging.info(
                f"Detected {str(AGENTFS_FILE)} in current working directory, will not load files."
            )
    mcp_wrapper: McpWrapper | None = None
    mcp_tools: list[Tool] | None = None
    if use_mcp:
        if mcp_config is not None:
            mcp_wrapper = McpWrapper.from_config_dict(mcp_config)
        elif MCP_CONFIG_FILE.exists() and MCP_CONFIG_FILE.is_file():
            mcp_wrapper = McpWrapper.from_file()
        else:
            rprint(
                "[yellow bold]WARNING[/]\tCannot use MCP if neither an MCP configuration dictionary nor an MCP config file are provided"
            )
    if mcp_wrapper is not None:
        logging.info("Starting to load all MCP tools...")
        mcp_tools = await mcp_wrapper.all_tools()
        logging.info("MCP tools loaded successfully!")
    if from_config_file:
        return AcpAgentWorkflow.ext_from_config_file(
            mcp_wrapper=mcp_wrapper,
            mcp_tools=mcp_tools,
            use_agentfs=use_agentfs,
        )
    return AcpAgentWorkflow(
        llm_model=llm_model,
        agent_task=agent_task,
        tools=tools,
        mode=mode,
        mcp_wrapper=mcp_wrapper,
        mcp_tools=mcp_tools,
        use_agentfs=use_agentfs,
    )


async def start_agent(
    llm_model: str | None = None,
    agent_task: str | None = None,
    tools: list[Tool] | list[DefaultToolType] | None = None,
    mode: str | None = None,
    from_config_file: bool = False,
    mcp_config: McpServersConfig | None = None,
    use_mcp: bool = True,
    use_agentfs: bool = False,
    agentfs_skip_files: list[str] | None = None,
    agentfs_skip_dirs: list[str] | None = None,
):
    """
    Start the agent and run the ACP protocol server.

    Args:
        llm_model (str | None): LLM model to use.
        agent_task (str | None): Task description for the agent.
        tools (list[Tool] | list[DefaultToolType] | None): List of tools to use.
        mode (str | None): Mode identifier.
        from_config_file (bool): Whether to load from config file.
        mcp_config (McpServersConfig | None): MCP configuration.
        use_mcp (bool): Whether to use MCP.
    """
    logging.basicConfig(
        filename="app.log",
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    agent = await _create_agent(
        llm_model=llm_model,
        agent_task=agent_task,
        tools=tools,
        mode=mode,
        from_config_file=from_config_file,
        mcp_config=mcp_config,
        use_mcp=use_mcp,
        use_agentfs=use_agentfs,
        agentfs_skip_files=agentfs_skip_files,
        agentfs_skip_dirs=agentfs_skip_dirs,
    )
    await run_agent(agent=agent)
