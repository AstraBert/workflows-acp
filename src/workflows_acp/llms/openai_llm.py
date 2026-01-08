from openai import AsyncOpenAI
from typing import Type

from .models import ChatHistory, ChatMessage, BaseLLM
from .retry import retry
from ..models import StructuredSchemaT
from ..constants import DEFAULT_OPENAI_MODEL


class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str, model: str | None = None) -> None:
        super().__init__(api_key, model or DEFAULT_OPENAI_MODEL)
        self._client = AsyncOpenAI(api_key=self.api_key)

    @retry()
    async def generate_content(
        self, schema: Type[StructuredSchemaT], chat_history: ChatHistory
    ) -> StructuredSchemaT | None:
        response = await self._client.responses.parse(
            text_format=schema,
            model=self.model,
            input=chat_history.to_openai_message_history(),
        )
        chat_history.append(ChatMessage(role="assistant", content=response.output_text))
        return response.output_parsed
