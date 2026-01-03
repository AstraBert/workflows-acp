import os

from typing import Type
from google.genai.types import Content, Part, GenerateContentConfig
from google.genai import Client as GenAIClient
from .models import Tool, StructuredSchemaT
from ._templating import Template
from .constants import SYSTEM_PROMPT_STRING, DEFAULT_MODEL, DEFAULT_TASK, AGENTS_MD

SYSTEM_PROMPT_TEMPLATE = Template(content=SYSTEM_PROMPT_STRING)


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
        """
        Add message from the user.

        Args:
            content (str): Content of the user's message
        """
        self._chat_history.append(
            Content(role="user", parts=[Part.from_text(text=content)])
        )

    async def generate(
        self, schema: Type[StructuredSchemaT]
    ) -> StructuredSchemaT | None:
        """
        Generate a response, based on previous chat history, following a JSON schema.

        Args:
            schema (Type[StructuredSchemaT]): Schema for structured generation by the underlying LLM client. Must be a Pydantic `BaseModel` subclass.

        Returns:
            SturcturedSchemaT | None: a Pydantic object following the input schema if the generation was successfull, None otherwise.
        """
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
        """
        Get a tool definition by its name.

        Args:
            tool_name (str): Name of the tool.

        Returns:
            Tool: tool definition (if the tool is available).
        """
        tools = [tool for tool in self.tools if tool.name == tool_name]
        assert len(tools) == 1
        return tools[0]
