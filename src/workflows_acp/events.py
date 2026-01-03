from workflows.events import (
    Event,
    StopEvent,
    StartEvent,
    InputRequiredEvent,
    HumanResponseEvent,
)
from typing import Any, Literal


class InputEvent(StartEvent):
    """
    Input event for the LlamaIndex Workflow

    Attributes:
        prompt (str): the initial prompt
        mode (Literal["ask", "bypass"]): the tool permission mode for the agent.
    """

    prompt: str
    mode: Literal["ask", "bypass"]


class PromptEvent(Event):
    """
    Event produced by an observation step in the LlamaIndex Workflow.

    Attributes:
        prompt (str): the prompt for the agent, deriving from the observation.
    """

    prompt: str


class ThinkingEvent(Event):
    """
    Event produced by a thinking step in the LlamaIndex Workflow.

    Attributes:
        content (str): the content of the thinking.
    """

    content: str


class ToolPermissionEvent(InputRequiredEvent):
    """
    Event produced by a tool call event in the LlamaIndex Workflow when the permission mode is set to 'ask'. Prompts input from the user.

    Attributes:
        tool_name (str): Name of the tool to execute.
        tool_input (dict[str, Any]): Arguments for tool execution.
    """

    tool_name: str
    tool_input: dict[str, Any]


class PermissionResponseEvent(HumanResponseEvent):
    """
    Event produced by the human response to a tool permission request.

    Attributes:
        allow (bool): Whether or not the human allows the tool call.
        reason (str | None): What is the reason for not allowing the tool call.
        tool_name (str): Name of the tool to be executed.
        tool_input (dict[str, Any]): Arguments for tool execution.
    """

    allow: bool
    reason: str | None
    tool_name: str
    tool_input: dict[str, Any]


class ToolCallEvent(Event):
    """
    Event that prompts a tool call.

    Attributes:
        tool_name (str): Name of the tool to be executed.
        tool_input (dict[str, Any]): Arguments for tool execution.
    """

    tool_name: str
    tool_input: dict[str, Any]


class ToolResultEvent(Event):
    """
    Event reporting the result of a tool call.

    Attributes:
        tool_name (str): Name of the executed tool.
        result (Any): Result from tool execution.
    """

    tool_name: str
    result: Any


class OutputEvent(StopEvent):
    """
    Final event of the LlamaIndex Workflow.


    """

    stop_reason: str | None = None
    final_output: str | None = None
    error: str | None = None
