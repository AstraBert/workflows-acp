"""
Simple agent implementation showing how to create custom tools.
"""

import asyncio

from workflows_acp.models import Tool
from workflows_acp.acp_wrapper import start_agent


def add(x: int, y: int) -> int:
    return x + y


def subtract(x: int, y: int) -> int:
    return x - y


def multiply(x: int, y: int) -> int:
    return x * y


def divide(x: int, y: int) -> str | float:
    if y == 0:
        return "Cannot divide by 0"
    return x / y


add_tool = Tool(
    name="add",
    description="Add two integers together",
    fn=add,
)

subtract_tool = Tool(
    name="subtract",
    description="Subtract the second integer from the first",
    fn=subtract,
)

multiply_tool = Tool(
    name="multiply",
    description="Multiply two integers together",
    fn=multiply,
)

divide_tool = Tool(
    name="divide",
    description="Divide the first integer by the second. Returns an error message if dividing by zero.",
    fn=divide,
)

AGENT_TASK = "You provide the user with assistance related to calculations, leveraging your tools to perform sums, subtractions, multiplications and divisions."


async def main() -> None:
    await start_agent(
        agent_task=AGENT_TASK,
        tools=[add_tool, subtract_tool, multiply_tool, divide_tool],
        use_mcp=False,
    )


if __name__ == "__main__":
    # execute with toad (or any other ACP client)
    # with toad:
    # toad acp "python3 /path/to/calculator.py"
    asyncio.run(main())
