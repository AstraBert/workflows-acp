from google.genai.types import (
    Content,
    GenerateContentResponse,
    Candidate,
    Part,
)
from google.genai import Client as GenAIClient
from typing import Any, AsyncGenerator, cast
from mcp_use.client.session import Tool as McpTool
from workflows.events import Event
from workflows_acp.models import Stop, Action, Tool
from workflows_acp.events import (
    ToolCallEvent,
    ThinkingEvent,
    PromptEvent,
    OutputEvent,
    ToolResultEvent,
)
from workflows_acp.llm_wrapper import LLMWrapper
from workflows_acp.mcp_wrapper import (
    HttpMcpServer,
    StdioMcpServer,
    McpServersConfig,
    McpWrapper,
)
from acp.schema import RequestPermissionResponse, AllowedOutcome


class MockModels:
    async def generate_content(self, *args, **kwargs) -> GenerateContentResponse:
        return GenerateContentResponse(
            candidates=[
                Candidate(
                    content=Content(
                        role="assistant",
                        parts=[
                            Part.from_text(
                                text=Action(
                                    type="stop",
                                    stop=Stop(
                                        stop_reason="I am done",
                                        final_output="this is a final result",
                                    ),
                                    tool_call=None,
                                ).model_dump_json()
                            )
                        ],
                    )
                )
            ]
        )


class MockAio:
    @property
    def models(self):
        return MockModels()


class MockGenAIClient:
    def __init__(self, api_key: str) -> None:
        return None

    @property
    def aio(self) -> MockAio:
        return MockAio()


class MockMcpSession:
    def __init__(self, *args, **kwargs) -> None:
        self._tools: list[McpTool] | None = kwargs.get("tools")
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def connect(self) -> None:
        self._is_connected = True
        return None

    async def list_tools(self) -> list[McpTool] | None:
        return self._tools

    async def call_tool(self, *args, **kwargs) -> Any:
        return f"Called tool {kwargs.get('name', 'no_name')} with arguments: {kwargs.get('arguments', '{}')}"


MCP_TOOLS = [
    McpTool(
        name="add",
        title="Addition Tool",
        description="Add to integers together",
        inputSchema={"x": "number", "y": "number"},
        outputSchema={"result": "number"},
    )
]

MCP_CONFIG = McpServersConfig(
    mcpServers={
        "with-stdio": StdioMcpServer(command="npx", args=["@mcp/server"], env=None),
        "with-http": HttpMcpServer(
            url="https://example.com/mcp",
            headers=None,
        ),
    }
)

MCP_CONFIG_ONE = McpServersConfig(
    mcpServers={
        "with-stdio": StdioMcpServer(command="npx", args=["@mcp/server"], env=None),
    }
)


class MockMcpClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    @classmethod
    def from_dict(cls, *args, **kwargs) -> "MockMcpClient":
        return cls(*args, **kwargs)

    async def create_session(self, *args, **kwargs) -> MockMcpSession:
        return MockMcpSession(tools=MCP_TOOLS)


class MockWorkflowHandler:
    def __init__(self, *args, **kwargs) -> None:
        self._events: list[Event] = [
            ThinkingEvent(content="thought"),
            ToolCallEvent(tool_name="say_hello", tool_input={}),
            ToolResultEvent(tool_name="say_hello", result="hello"),
            PromptEvent(prompt="we are done"),
            OutputEvent(stop_reason="done", final_output="hello", error=None),
        ]
        self._log_file = "app.log"

    async def stream_events(self, *args, **kwargs) -> AsyncGenerator[Event, Any]:
        for event in self._events:
            with open(self._log_file, "a") as f:
                ev_type = event.__repr_name__().split(".")[-1]
                f.write(ev_type + "\n")
            yield event

    def __await__(self):
        async def _init():
            # Put any async initialization here
            return OutputEvent(stop_reason="done", final_output="hello")

        return _init().__await__()


class MockWorkflow:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def run(self, *args, **kwargs) -> MockWorkflowHandler:
        return MockWorkflowHandler()


class MockMcpWrapper(McpWrapper):
    def __init__(
        self, mcp_servers: dict[str, Any], from_config_dict: bool = False
    ) -> None:
        self._client = MockMcpClient()
        self.mcp_servers = MCP_CONFIG_ONE


class MockLLMWrapper(LLMWrapper):
    def __init__(
        self,
        tools: list[Tool],
        agent_task: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        super().__init__(tools, agent_task, api_key, model)
        self._client = cast(GenAIClient, MockGenAIClient(api_key=""))


class MockACPClient:
    def __init__(self, *args, **kwargs) -> None:
        self.num_updates = 0

    async def session_update(self, *args, **kwargs) -> Any:
        self.num_updates += 1

    async def request_permission(self, *args, **kwargs) -> RequestPermissionResponse:
        return RequestPermissionResponse(
            outcome=AllowedOutcome(outcome="selected", option_id="allow")
        )
