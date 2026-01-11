from typing import Type
from google.genai import Client as GenAIClient
from google.genai.types import GenerateContentConfig

from .retry import retry
from .models import ChatHistory, ChatMessage, BaseLLM
from ..models import StructuredSchemaT
from ..constants import DEFAULT_GOOGLE_MODEL


class GoogleLLM(BaseLLM):
    def __init__(self, api_key: str, model: str | None = None) -> None:
        super().__init__(api_key, model or DEFAULT_GOOGLE_MODEL)
        self._client = GenAIClient(api_key=self.api_key)

    @retry()
    async def generate_content(
        self, schema: Type[StructuredSchemaT], chat_history: ChatHistory
    ) -> StructuredSchemaT | None:
        system_prompt, messages = chat_history.to_google_message_history()
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=messages,
            config=GenerateContentConfig(
                response_json_schema=schema.model_json_schema(),
                response_mime_type="application/json",
                system_instruction=system_prompt,
            ),
        )
        if response.candidates is not None:
            if response.candidates[0].content is not None:
                chat_history.append(
                    ChatMessage(role="assistant", content=response.text or "")
                )
            if response.text is not None:
                return schema.model_validate_json(response.text)
        return None
