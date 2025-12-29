from workflows.events import Event, StopEvent, StartEvent, InputRequiredEvent, HumanResponseEvent
from typing import Any, Literal

class InputEvent(StartEvent):
    prompt: str
    mode: Literal["ask", "bypass"]

class PromptEvent(Event):
    prompt: str

class ThinkingEvent(Event):
    content: str

class ObservationEvent(Event):
    content: str

class AskHumanEvent(InputRequiredEvent):
    question: str

class HumanAnswerEvent(HumanResponseEvent):
    answer: str

class ToolPermissionEvent(InputRequiredEvent):
    tool_name: str
    tool_input: dict[str, Any]

class PermissionResponseEvent(HumanResponseEvent):
    allow: bool
    reason: str | None

class ToolCallEvent(Event):
    tool_name: str
    tool_input: dict[str, Any]

class ToolResultEvent(Event):
    tool_name: str
    result: Any    

class OutputEvent(StopEvent):
    stop_reason: str | None = None
    final_output: str | None = None
    error: str | None = None
