from dataclasses import dataclass
from abc import abstractmethod, ABC
from typing import Literal, TypedDict, Any, Type, cast
from google.genai.types import Content, Part
from openai.types.responses.easy_input_message_param import EasyInputMessageParam
from anthropic.types.beta.beta_message_param import BetaMessageParam
from ..models import StructuredSchemaT


class OpenAIMessage(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str


@dataclass
class ChatMessage:
    role: Literal["user", "assistant", "system"]
    content: str

    def to_google_message(self) -> Content | Part:
        if self.role != "system":
            role = self.role if self.role == "user" else "model"
            return Content(role=role, parts=[Part.from_text(text=self.content)])
        else:
            return Part.from_text(text=self.content)

    def to_openai_message(self) -> EasyInputMessageParam:
        return EasyInputMessageParam(
            role=self.role, content=self.content, type="message"
        )

    def to_anthropic_message(self) -> BetaMessageParam | str:
        if self.role != "system":
            return BetaMessageParam(content=self.content, role=self.role)
        return self.content


@dataclass
class ChatHistory:
    messages: list[ChatMessage]

    def append(self, message: ChatMessage) -> None:
        self.messages.append(message)

    def to_google_message_history(self) -> tuple[list[Part], list[Content]]:
        system_prompt: list[Part] = [
            cast(Part, message.to_google_message())
            for message in self.messages
            if message.role == "system"
        ]
        contents: list[Content] = [
            cast(Content, message.to_google_message())
            for message in self.messages
            if message.role != "system"
        ]
        return system_prompt, contents

    def to_openai_message_history(self) -> list[Any]:
        return [message.to_openai_message() for message in self.messages]

    def to_anthropic_message_history(self) -> tuple[str, list[BetaMessageParam]]:
        system_prompt = "\n".join(
            [
                cast(str, message.to_anthropic_message())
                for message in self.messages
                if message.role == "system"
            ]
        )
        return system_prompt, [
            cast(BetaMessageParam, message.to_anthropic_message())
            for message in self.messages
            if message.role != "system"
        ]


class BaseLLM(ABC):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def generate_content(
        self,
        schema: Type[StructuredSchemaT],
        chat_history: ChatHistory,
    ) -> StructuredSchemaT | None: ...
