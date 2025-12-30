import os

from typing import Type
from pathlib import Path
from google.genai.types import Content, Part, GenerateContentConfig
from google.genai import Client as GenAIClient
from .models import Tool, StructuredSchemaT
from ._templating import Template

SYSTEM_PROMPT_STRING = """
## Main Task

You are a helpful assistant whose main task is:

```md
{{task}}
```

## Methods

In order to accomplish this task, you will be asked to:

- **Think**: reflect on the user's request and on what you have already done (available through chat history)
- **Act**: Take an action based on the current situation and informed by the chat history. The action might be:
    + A tool call (using one of the available tools, listed in the `Tools` section)
    + A question to the user (human in the loop)
    + A stop call (providing a stop reason and a final result)
- **Observe**: Following tool calls, you will observe/summarize the current situation in order to inform the thinking step about tool results and potential scenarios moving forward.

## Tools

{{tools}}
{{additional_instructions}}
"""

SYSTEM_PROMPT_TEMPLATE = Template(content=SYSTEM_PROMPT_STRING)

DEFAULT_TASK = """
Assist the user with their requests, leveraging the tools available to you (as per the `Tools` section) and following the think -> act -> observe pattern detailed in the `Methods` section.
"""

DEFAULT_MODEL = "gemini-3-flash-preview"
AGENTS_MD = Path("AGENTS.md")


def _check_tools(tools: list[Tool]) -> bool:
    names = [tool.name for tool in tools]
    return len(names) == len(set(names))


class LLMWrapper:
    """
    Wrapper for Google GenAI LLM to generalize structured generation and extend agentic capabilities.
    """

    def __init__(
        self,
        tools: list[Tool],
        agent_task: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        """
        Initialize LLMWrapper.

        Args:
            tools (list[Tool]): List of tool defitions for the LLM to use
            agent_task (str | None): Optional specific task that the agent has to accomplish on behalf of the user.
            api_key (str | None): Optional API key for Google GenAI. Inferred from environment if not provided.
            model (str | None): LLM model to use. Defaults to `gemini-3-flash`.
        """
        if api_key is None:
            api_key = os.getenv("GOOGLE_API_KEY")
        if api_key is None:
            raise ValueError(
                "GOOGLE_API_KEY not found within the current environment: please export it or provide it to the class constructor."
            )
        if not _check_tools(tools=tools):
            raise ValueError("All the tools provided should have different names")
        if AGENTS_MD.exists():
            additional_instructions = (
                "## Additional Instructions\n\n```md\n"
                + AGENTS_MD.read_text()
                + "\n```\n"
            )
        else:
            additional_instructions = ""
        task = agent_task or DEFAULT_TASK
        tools_str = "\n\n".join([tool.to_string() for tool in tools])
        system_prompt = SYSTEM_PROMPT_TEMPLATE.render(
            {
                "task": task,
                "tools": tools_str,
                "additional_instructions": additional_instructions,
            }
        )
        self.tools = tools
        self._client = GenAIClient(api_key=api_key)
        self._chat_history: list[Content] = [
            Content(role="system", parts=[Part.from_text(text=system_prompt)])
        ]
        self.model = model or DEFAULT_MODEL

    def add_user_message(self, content: str) -> None:
        self._chat_history.append(
            Content(role="user", parts=[Part.from_text(text=content)])
        )

    async def generate(
        self, schema: Type[StructuredSchemaT]
    ) -> StructuredSchemaT | None:
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=self._chat_history,  # type: ignore
            config=GenerateContentConfig(
                response_json_schema=schema.model_json_schema(),
                response_mime_type="application/json",
            ),
        )
        if response.candidates is not None:
            if response.candidates[0].content is not None:
                self._chat_history.append(response.candidates[0].content)
            if response.text is not None:
                return schema.model_validate_json(response.text)
        return None

    def get_tool(self, tool_name: str) -> Tool:
        tools = [tool for tool in self.tools if tool.name == tool_name]
        assert len(tools) == 1
        return tools[0]
