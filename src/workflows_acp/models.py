import inspect

from pydantic import BaseModel, Field
from typing import Literal, Any, Callable, TypedDict, NotRequired, TypeVar
from .events import ThinkingEvent, ObservationEvent, ToolCallEvent, OutputEvent, AskHumanEvent, ToolPermissionEvent

ActionType = Literal["tool_call", "stop", "ask_human"]
StructuredSchemaT = TypeVar("StructuredSchemaT", bound=BaseModel)

class Thought(BaseModel):
    """Represents a thought or internal reasoning step."""
    content: str = Field(description="The content of the thought.")

    def to_event(self) -> ThinkingEvent:
        return ThinkingEvent(**self.model_dump())

class Observation(BaseModel):
    """Represents an observation or perception from the environment."""
    content: str = Field(description="The content of the observation.")

    def to_event(self) -> ObservationEvent:
        return ObservationEvent(**self.model_dump())

class ToolCallArg(BaseModel):
    """Represents a single argument for a tool call."""
    arg_name: str = Field(description="The name of the argument for the tool call.")
    arg_value: Any = Field(description="The value of the argument for the tool call.")

class ToolCall(BaseModel):
    """Represents a call to a tool with its input arguments."""
    tool_name: str = Field(description="The name of the tool to call.")
    tool_input: list[ToolCallArg] = Field(description="The list of arguments to pass to the tool.")

class Stop(BaseModel):
    """Represents the stopping condition and final output of an action sequence."""
    stop_reason: str = Field(description="The reason for stopping.")
    final_output: str = Field(description="The final output produced when stopping.")

class AskHuman(BaseModel):
    """Represents a request to ask a human a question."""
    question: str = Field(description="The question to ask the human.")

class Action(BaseModel):
    """Represents an action, which can be a tool call, stop action, or ask human action."""
    type: ActionType = Field(description="The type of action: 'tool_call', 'stop', or 'ask_human'.")
    tool_call: ToolCall | None = Field(description="The tool call details if the action is a tool call, otherwise None.")
    stop: Stop | None = Field(description="The stop details if the action is a stop, otherwise None.")
    ask_human: AskHuman | None = Field(description="The ask human details if the action is an ask_human, otherwise None.")

    def to_event(self) -> ToolCallEvent | OutputEvent | AskHumanEvent:
        if self.type == "stop":
            assert self.stop is not None
            return OutputEvent(**self.stop.model_dump())
        elif self.type == "tool_call":
            assert self.tool_call is not None
            args = {}
            for arg in self.tool_call.tool_input:
                args[arg.arg_name] = arg.arg_value
            return ToolCallEvent(tool_name=self.tool_call.tool_name, tool_input=args)
        else:
            assert self.ask_human is not None
            return AskHumanEvent(**self.ask_human.model_dump())

class ParameterMetadata(TypedDict):
    """Represents metadata for a parameter from a function"""
    type: str | None
    required: bool
    default: NotRequired[Any]

class Tool(BaseModel):
    """Represents the defition of a tool
    
    Attributes:
        name (str): the name of the tool
        description (str): the description of the tool function
        fn (Callbale): the function to be called alongside the tool
    """
    name: str
    description: str
    fn: Callable

    def _get_fn_metadata(self) -> dict[str, ParameterMetadata]:
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
        base = f"Tool Name: {self.name}\nTool Description: {self.description}\nTool Parameters:"
        fn_metadata = self._get_fn_metadata()
        for param in fn_metadata:
            tp = f" ({fn_metadata[param]['type']})" if fn_metadata[param]['type'] is not None else ''
            req = 'required' if fn_metadata[param]['required'] else f'not required (default: {fn_metadata[param].get("default")})'
            base += f"\n- `{param}`{tp} - {req}"
        return base
                
    async def execute(self, args: dict[str, Any]) -> Any:
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
    
    def get_permission(self, args: dict[str, Any]) -> ToolPermissionEvent:
        return ToolPermissionEvent(tool_name=self.name, tool_input=args)