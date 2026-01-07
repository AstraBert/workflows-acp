import os

from typing import Type, Literal
from .models import Tool, StructuredSchemaT
from ._templating import Template
from .constants import SYSTEM_PROMPT_STRING, DEFAULT_MODEL, DEFAULT_TASK, AGENTS_MD
from .llms import GoogleLLM, OpenAILLM, AnthropicLLM, ChatHistory, ChatMessage

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
        llm_provider: Literal["google", "anthropic", "openai"] = "google",
    ):
        """
        Initialize LLMWrapper.

        Args:
            tools (list[Tool]): List of tool defitions for the LLM to use
            agent_task (str | None): Optional specific task that the agent has to accomplish on behalf of the user.
            api_key (str | None): Optional API key for Google GenAI. Inferred from environment if not provided.
            model (str | None): LLM model to use. Defaults to `gemini-3-flash`.
        """
        api_key_variable = f"{llm_provider.upper()}_API_KEY"
        if api_key is None:
            api_key = os.getenv(api_key_variable)
        if api_key is None:
            raise ValueError(
                f"{api_key_variable} not found within the current environment: please export it or provide it to the class constructor."
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
        if llm_provider == "anthropic":
            self._client = AnthropicLLM(api_key=api_key, model=model)
        elif llm_provider == "openai":
            self._client = OpenAILLM(api_key=api_key, model=model)
        else:
            self._client = GoogleLLM(api_key=api_key, model=model)
        self._chat_history: ChatHistory = ChatHistory(messages=[])
        self._chat_history.append(ChatMessage(role="system", content=system_prompt))
        self.model = model or DEFAULT_MODEL[llm_provider]

    def add_user_message(self, content: str) -> None:
        """
        Add message from the user.

        Args:
            content (str): Content of the user's message
        """
        self._chat_history.append(ChatMessage(role="user", content=content))

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
        response = await self._client.generate_content(
            chat_history=self._chat_history,
            schema=schema,
        )
        return response

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
