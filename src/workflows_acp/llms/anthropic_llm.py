from anthropic import AsyncAnthropic
from anthropic.types.beta.beta_message_param import BetaMessageParam
from typing import Type

from .models import ChatHistory, ChatMessage, BaseLLM
from .retry import retry
from ..models import StructuredSchemaT
from ..constants import DEFAULT_ANTHROPIC_MODEL


class AnthropicLLM(BaseLLM):
    def __init__(self, api_key: str, model: str | None = None) -> None:
        super().__init__(api_key, model or DEFAULT_ANTHROPIC_MODEL)
        self._client = AsyncAnthropic(api_key=self.api_key)

    @retry()
    async def generate_content(
        self, schema: Type[StructuredSchemaT], chat_history: ChatHistory
    ) -> StructuredSchemaT | None:
        system, messages = chat_history.to_anthropic_message_history()
        if messages[-1]["role"] == "assistant":
            # only happens when the LLM is prompted to take an action after thinking
            messages.append(
                BetaMessageParam(
                    content="Based on the previous message history, decide what action to take.",
                    role="user",
                )
            )
        response = await self._client.beta.messages.parse(
            max_tokens=8192,
            output_format=schema,
            model=self.model,
            system=system,
            messages=messages,
        )
        chat_history.append(
            ChatMessage(
                role="assistant",
                content=response.parsed_output.model_dump_json()
                if response.parsed_output is not None
                else "",
            )
        )
        return response.parsed_output
