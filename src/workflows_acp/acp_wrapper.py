import logging
import yaml
from typing import Any, cast, Literal
from datetime import datetime

from acp import (
    PROTOCOL_VERSION,
    Agent,
    AuthenticateResponse,
    InitializeResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptResponse,
    SetSessionModeResponse,
    update_agent_message,
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
    AgentMessageChunk,
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
    SessionMode,
    SessionInfo,
    PermissionOption,
)

from .workflow import AgentWorkflow
from .llm_wrapper import LLMWrapper
from .models import Tool
from .tools import TOOLS, DefaultToolType, filter_tools
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

MODES = [
    SessionMode(
        id="bypass",
        name="bypassToolPermission",
        description="Bypass asking for tool permission, executing tools directly (not recommended, use 'askToolPermission' instead)",
    ),
    SessionMode(
        id="ask",
        name="askToolPermission",
        description="Ask for tool usage permission before executing it.",
    ),
]
PERMISSION_OPTIONS = [
    PermissionOption(kind="allow_once", name="Allow", option_id="allow"),
    PermissionOption(kind="reject_once", name="Reject", option_id="reject"),
]
VERSION = "0.1.0"
DEFAULT_MODE_ID = "ask"


class AcpAgentWorkflow(Agent):
    _conn: Client

    def __init__(
        self,
        llm_model: str | None = None,
        agent_task: str | None = None,
        tools: list[Tool] | list[DefaultToolType] | None = None,
        mode: str | None = None,
    ) -> None:
        self._next_session_id = 0
        self._sessions: set[str] = set()
        self._session_infos: dict[str, SessionInfo] = {}
        self._mode: str = mode or DEFAULT_MODE_ID
        self._current_tool_call_id: int = 0
        _impl_tools: list[Tool] = TOOLS
        if tools is not None:
            first_item = next(iter(tools))
            if isinstance(first_item, Tool):
                _impl_tools = cast(list[Tool], tools)
            else:
                _impl_tools = filter_tools(names=cast(list[DefaultToolType], tools))
        self._llm = LLMWrapper(
            tools=_impl_tools, agent_task=agent_task, model=llm_model
        )

    @classmethod
    def ext_from_config_file(
        cls, config_file: str = "agent_config.yaml"
    ) -> "AcpAgentWorkflow":
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
        config: dict[str, Any] = {
            "agent_task": None,
            "llm_model": None,
            "tools": None,
            "mode": None,
        }
        if "agent_task" in data:
            config["agent_task"] = data["agent_task"]
        if "model" in data:
            config["llm_model"] = data["model"]
        if "tools" in data:
            assert isinstance(data["tools"], list)
            config["tools"] = cast(list[DefaultToolType], data["tools"])
        if "mode" in data:
            config["mode"] = data["mode"]
        return cls(**config)

    def _get_tool_call_id(self, increment: bool = True) -> str:
        if increment:
            self._current_tool_call_id += 1
            return f"call_{self._current_tool_call_id}"
        else:
            return f"call_{self._current_tool_call_id}"

    def on_connect(self, conn: Client) -> None:
        self._conn = conn

    async def _send_agent_message(self, session_id: str, content: Any) -> None:
        update = (
            content
            if isinstance(content, AgentMessageChunk)
            else update_agent_message(content)
        )
        await self._conn.session_update(session_id, update)

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: ClientCapabilities | None = None,
        client_info: Implementation | None = None,
        **kwargs: Any,
    ) -> InitializeResponse:
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
                name="workflows-acp", title="AgentWorkflow", version="0.1.0"
            ),
        )

    async def authenticate(
        self, method_id: str, **kwargs: Any
    ) -> AuthenticateResponse | None:
        logging.info("Received authenticate request %s", method_id)
        return AuthenticateResponse()

    async def new_session(
        self,
        cwd: str,
        mcp_servers: list[HttpMcpServer | SseMcpServer | McpServerStdio],
        **kwargs: Any,
    ) -> NewSessionResponse:
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
        logging.info("Received set session mode request %s -> %s", session_id, mode_id)
        self._mode = mode_id
        return SetSessionModeResponse()

    async def list_sessions(
        self, cursor: str | None = None, cwd: str | None = None, **kwargs: Any
    ) -> ListSessionsResponse:
        return ListSessionsResponse(sessions=list(self._session_infos.values()))

    async def set_session_model(
        self, model_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModelResponse | None:
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
        logging.info("Received prompt request for session %s", session_id)
        if session_id not in self._sessions:
            self._sessions.add(session_id)
        _impl_prompt = ""
        for block in prompt:
            if isinstance(block, TextContentBlock):
                _impl_prompt += block.text + "\n"
        wf = AgentWorkflow(llm=self._llm)
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
                tool_title = f"Resulf for tool {event.tool_name}"
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
        logging.info("Received cancel notification for session %s", session_id)

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        logging.info("Received extension method call: %s", method)
        return {"error": "External methods not supported"}

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        logging.info("Received extension notification: %s", method)


async def start_agent(
    llm_model: str | None = None,
    agent_task: str | None = None,
    tools: list[Tool] | list[DefaultToolType] | None = None,
    mode: str | None = None,
    config_file: str | None = None,
):
    logging.basicConfig(level=logging.INFO)
    if config_file is not None:
        agent = AcpAgentWorkflow.ext_from_config_file(config_file)
    else:
        agent = AcpAgentWorkflow(
            llm_model=llm_model, agent_task=agent_task, tools=tools, mode=mode
        )
    await run_agent(agent=agent)
