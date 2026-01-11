import pytest
import asyncio

from pydantic import ValidationError
from mcp_use.client.session import Tool as McpTool
from workflows_acp.models import (
    Tool,
    Action,
    Thought,
    Observation,
    ToolCall,
    Stop,
)
from workflows_acp.events import (
    ToolPermissionEvent,
    ThinkingEvent,
    PromptEvent,
    ToolCallEvent,
    OutputEvent,
)


@pytest.mark.asyncio
async def test_tool_sync() -> None:
    def add(x: int, y: int = 1) -> int:
        return x + y

    add_tool = Tool(
        name="add",
        description="Add two integers together",
        fn=add,
    )
    fn_meta = add_tool._get_fn_metadata()
    assert "x" in fn_meta and "y" in fn_meta
    assert "default" not in fn_meta["x"]
    assert fn_meta["x"]["required"]
    assert fn_meta["x"]["type"] == str(int)
    assert "default" in fn_meta["y"] and fn_meta["y"]["default"] == 1
    assert not fn_meta["y"]["required"]
    assert fn_meta["y"]["type"] == str(int)
    assert (
        add_tool.to_string()
        == "Tool Name: add\nTool Description: Add two integers together\nTool Parameters:\n- `x` (<class 'int'>) - required\n- `y` (<class 'int'>) - not required (default: 1)"
    )
    result = await add_tool.execute({"x": 1, "y": 2})
    assert result == 3
    permission = add_tool.get_permission({"x": 1, "y": 2})
    assert isinstance(permission, ToolPermissionEvent)
    assert permission.tool_name == "add"
    assert permission.tool_input == {"x": 1, "y": 2}

    def divide(x: int, y: int) -> float:
        return x / y

    add_tool.fn = divide
    result = await add_tool.execute({"x": 1, "y": 0})
    assert (
        result
        == "An error occurred while calling tool add with arguments: {'x': 1, 'y': 0}: division by zero"
    )

    add_tool.fn = None

    with pytest.raises(
        AssertionError, match="Function should be non-null for tool execution"
    ):
        await add_tool.execute({"x": 1, "y": 0})
    with pytest.raises(
        AssertionError, match="Function should be not-null to get its metadata"
    ):
        add_tool._get_fn_metadata()


@pytest.mark.asyncio
async def test_tool_async() -> None:
    async def process_orders(order_ids: list[int]) -> str:
        for order in order_ids:
            print("Processed:", order)
            await asyncio.sleep(0)
        return "SUCCESS"

    process_tool = Tool(
        name="process_orders",
        description="Process orders based on their IDs",
        fn=process_orders,
    )
    result = await process_tool.execute({"order_ids": ["1", "2"]})
    assert result == "SUCCESS"


@pytest.mark.asyncio
async def test_tool_from_mcp() -> None:
    mcp_tool = McpTool(
        name="add",
        title="Addition Tool",
        description="Add to integers together",
        inputSchema={"x": "number", "y": "number"},
        outputSchema={"result": "number"},
    )
    tool = Tool.from_mcp_tool(mcp_tool, "math")
    assert tool.name == "mcp_add"
    assert tool.description == "Add to integers together"
    assert tool.mcp_metadata is not None
    assert tool.mcp_metadata["input_schema"] == {"x": "number", "y": "number"}
    assert tool.mcp_metadata["output_schema"] == {"result": "number"}
    assert tool.mcp_metadata["server"] == "math"
    assert tool.fn is None
    assert (
        tool.to_string()
        == 'Tool Name: mcp_add\nTool Description: Add to integers together\nFrom MCP Server: math\nTool Input Schema:\n\n```json\n{\n  "x": "number",\n  "y": "number"\n}\n```\n\n\nTool Output Schema:\n\n```json\n{\n  "result": "number"\n}\n```\n\n'
    )

    with pytest.raises(
        AssertionError, match="Function should be non-null for tool execution"
    ):
        await tool.execute({"x": 1, "y": 0})

    with pytest.raises(ValidationError):
        # tool cannot start with `mcp_` if it does not have any
        # MCP metadata
        Tool(name="mcp_add", description="Something", fn=None, mcp_metadata=None)


def test_model_to_event() -> None:
    thought = Thought(content="hello")
    thinking_event = thought.to_event()
    assert isinstance(thinking_event, ThinkingEvent)
    assert thinking_event.content == "hello"
    obs = Observation(content="hello")
    obs_event = obs.to_event()
    assert isinstance(obs_event, PromptEvent)
    assert obs_event.prompt == "hello"
    action_tc = Action(
        action_type="tool_call",
        tool_call=ToolCall(
            tool_name="add",
            tool_input='{"x": 1, "y": 2}',
        ),
        stop=None,
    )
    action_tc_event = action_tc.to_event()
    assert isinstance(action_tc_event, ToolCallEvent)
    assert action_tc_event.tool_input == {"x": 1, "y": 2}
    assert action_tc_event.tool_name == "add"
    action_st = Action(
        action_type="stop",
        tool_call=None,
        stop=Stop(stop_reason="why", final_output="hello"),
    )
    action_st_event = action_st.to_event()
    assert isinstance(action_st_event, OutputEvent)
    assert action_st_event.final_output == "hello"
    assert action_st_event.error is None
    assert action_st_event.stop_reason == "why"

    with pytest.raises(AssertionError):
        Action(action_type="stop", tool_call=None, stop=None).to_event()

    with pytest.raises(AssertionError):
        Action(action_type="tool_call", tool_call=None, stop=None).to_event()
