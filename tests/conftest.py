from google.genai.types import (
    Content,
    GenerateContentResponse,
    Candidate,
    Part,
)
from typing import Any
from mcp_use.client.session import Tool as McpTool
from workflows_acp.models import Stop, Action


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


class MockMcpClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    @classmethod
    def from_dict(cls, *args, **kwargs) -> "MockMcpClient":
        return cls(*args, **kwargs)

    async def create_session(self, *args, **kwargs) -> MockMcpSession:
        return MockMcpSession(tools=MCP_TOOLS)
