import inspect
import json

from pydantic import BaseModel, Field, model_validator
from typing import Literal, Any, Callable, TypeVar
from typing_extensions import TypedDict
from typing_extensions import NotRequired, Self
from mcp_use.client.session import Tool as McpTool
from .events import (
    ThinkingEvent,
    ToolCallEvent,
    OutputEvent,
    ToolPermissionEvent,
    PromptEvent,
)

ActionType = Literal["tool_call", "stop"]
AvailableModel = Literal[
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
    "claude-opus-4-5",
    "claude-sonnet-4-5",
    "claud-haiku-4-5",
    "claude-opus-4-1",
    "claude-sonnet-4-0",
    "gpt-4.1",
    "gpt-5",
    "gpt-5.1",
    "gpt-5.2",
]
StructuredSchemaT = TypeVar("StructuredSchemaT", bound=BaseModel)


class Thought(BaseModel):
    """Represents a thought or internal reasoning step."""

    content: str = Field(description="The content of the thought.")

    def to_event(self) -> ThinkingEvent:
        """Convert the instance into a ThinkingEvent."""
        return ThinkingEvent(**self.model_dump())


class Observation(BaseModel):
    """Represents an observation or perception from the environment."""

    content: str = Field(description="The content of the observation.")

    def to_event(self) -> PromptEvent:
        """Convert the instance into a PromptEvent."""
        return PromptEvent(prompt=self.content)


class ToolCall(BaseModel):
    """Represents a call to a tool with its input arguments."""

    tool_name: str = Field(description="The name of the tool to call.")
    tool_input: str = Field(
        description="A JSON-serializable string representing the input for the tool, based on the tool's schema. Example: '{'file_path': 'hello.py'}'. Produce only complete JSON."
    )

    def args_to_dict(self) -> dict[str, Any]:
        # let the error bubble up if serdes op fails
        return json.loads(self.tool_input)


class Stop(BaseModel):
    """Represents the stopping condition and final output of an action sequence."""

    stop_reason: str = Field(description="The reason for stopping.")
    final_output: str = Field(description="The final output produced when stopping.")


class Action(BaseModel):
    """Represents an action, which can be a tool call, stop action, or ask human action."""

    action_type: ActionType = Field(
        description="The type of action: 'tool_call' or 'stop'."
    )
    tool_call: ToolCall | None = Field(
        description="The tool call details if the action is a tool call, otherwise None."
    )
    stop: Stop | None = Field(
        description="The stop details if the action is a stop, otherwise None."
    )

    def to_event(self) -> ToolCallEvent | OutputEvent:
        """Convert the instance into a ToolCallEvent or into an OutputEvent (based on the action type)."""
        if self.action_type == "stop":
            assert self.stop is not None
            return OutputEvent(**self.stop.model_dump())
        else:
            assert self.tool_call is not None
            return ToolCallEvent(
                tool_name=self.tool_call.tool_name,
                tool_input=self.tool_call.args_to_dict(),
            )


class ParameterMetadata(TypedDict):
    """Represents metadata for a parameter from a function"""

    type: str | None
    required: bool
    default: NotRequired[Any]


class McpMetadata(TypedDict):
    """Represents the metadata for an MCP tool"""

    server: str
    input_schema: dict[str, Any] | None
    output_schema: dict[str, Any] | None


class Tool(BaseModel):
    """Represents the defition of a tool

    Attributes:
        name (str): the name of the tool
        description (str): the description of the tool function
        fn (Callbale): the function to be called alongside the tool
        mcp_metadata (McpMetadata | None): metadata for MCP tools
    """

    name: str
    description: str
    fn: Callable | None
    mcp_metadata: McpMetadata | None = None

    @classmethod
    def from_mcp_tool(cls, mcp_tool: McpTool, server_name: str) -> "Tool":
        """
        Initialize a Tool from an MCP tool.

        Args:
            mcp_tool (McpTool): Tool as defined by the MCP server
            server_name: Name of the server in which the tool is defined

        Returns:
            Tool: Tool definition.
        """
        return cls(
            name="mcp_" + mcp_tool.name,
            description=mcp_tool.description or "",
            fn=None,
            mcp_metadata=McpMetadata(
                server=server_name,
                input_schema=mcp_tool.inputSchema,
                output_schema=mcp_tool.outputSchema,
            ),
        )

    def _get_fn_metadata(self) -> dict[str, ParameterMetadata]:
        assert self.fn is not None, "Function should be not-null to get its metadata"
        sign = inspect.signature(self.fn)
        parameters: dict[str, ParameterMetadata] = {}
        for param in sign.parameters.values():
            metadata = ParameterMetadata(type=None, required=True)
            if param.annotation is not inspect._empty:
                metadata["type"] = str(param.annotation)
            if param.default is not inspect._empty:
                metadata["required"] = False
                metadata["default"] = param.default
            parameters.update({param.name: metadata})
        return parameters

    def to_string(self) -> str:
        """
        Transform the tool metadata into an LLM-friendly tool description
        """
        base = f"Tool Name: {self.name}\nTool Description: {self.description}"
        if self.mcp_metadata is None:
            base += "\nTool Parameters:"
            fn_metadata = self._get_fn_metadata()
            for param in fn_metadata:
                tp = (
                    f" ({fn_metadata[param]['type']})"
                    if fn_metadata[param]["type"] is not None
                    else ""
                )
                req = (
                    "required"
                    if fn_metadata[param]["required"]
                    else f"not required (default: {fn_metadata[param].get('default')})"
                )
                base += f"\n- `{param}`{tp} - {req}"
        else:
            if self.mcp_metadata["input_schema"] is not None:
                base += f"\nFrom MCP Server: {self.mcp_metadata['server']}"
                try:
                    inpt_schema = json.dumps(
                        self.mcp_metadata["input_schema"], indent=2
                    )
                except Exception:
                    inpt_schema = str(self.mcp_metadata["input_schema"])
                base += f"\nTool Input Schema:\n\n```json\n{inpt_schema}\n```\n\n"
            if self.mcp_metadata["output_schema"] is not None:
                try:
                    outpt_schema = json.dumps(
                        self.mcp_metadata["output_schema"], indent=2
                    )
                except Exception:
                    outpt_schema = str(self.mcp_metadata["output_schema"])
                base += f"\nTool Output Schema:\n\n```json\n{outpt_schema}\n```\n\n"
        return base

    async def execute(self, args: dict[str, Any]) -> Any:
        """
        Execute the tool given a dictionary of arguments.

        Args:
            args (dict[str, Any]): Arguments for the tool call
        """
        assert self.fn is not None, "Function should be non-null for tool execution"
        if inspect.iscoroutinefunction(self.fn):
            try:
                result = await self.fn(**args)
            except Exception as e:
                result = f"An error occurred while calling tool {self.name} with arguments: {args}: {e}"
            return result
        else:
            try:
                result = self.fn(**args)
            except Exception as e:
                result = f"An error occurred while calling tool {self.name} with arguments: {args}: {e}"
            return result

    def get_permission(self, args: dict[str, Any]) -> ToolPermissionEvent:
        """
        Emits an event to get permission for executing a tool.

        Args:
            args (dict[str, Any]): Arguments for the tool call
        """
        return ToolPermissionEvent(tool_name=self.name, tool_input=args)

    @model_validator(mode="after")
    def name_validator(self) -> Self:
        if self.name.startswith("mcp_") and self.mcp_metadata is None:
            raise ValueError(
                "A tool whose name starts with `mcp_` must have a non-null mcp_metadata field. If this is not an MCP tool, please rename it to something else."
            )
        if not self.name.startswith("mcp_") and self.mcp_metadata is not None:
            raise ValueError(
                "A tool whose name does not start with `mcp_` cannot have a non-null mcp_metadata field. If this is an MCP tool, please rename it so that its name starts with `mcp_`."
            )
        return self
