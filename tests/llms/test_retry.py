import pytest
import time

from typing import Type
from pydantic import BaseModel
from workflows_acp.llms.retry import retry
from workflows_acp.llms.models import BaseLLM, ChatHistory
from workflows_acp.models import StructuredSchemaT


class StableLLM(BaseLLM):
    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(api_key, model)
        self.has_retried = False

    @retry(retry_interval=0.01)
    async def generate_content(
        self, schema: Type[StructuredSchemaT], chat_history: ChatHistory
    ) -> StructuredSchemaT | None:
        if not self.has_retried:
            self.has_retried = True
            raise ValueError("Has not retried yet")
        else:
            return schema()


class UnstableLLM(BaseLLM):
    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(api_key, model)
        self.retry_times = 0
        self.retry_times_exp = 0

    @retry(
        retry_interval=0.01,
        max_retries=5,
        max_retry_interval=0.03,
    )
    async def generate_content(
        self, schema: Type[StructuredSchemaT], chat_history: ChatHistory
    ) -> StructuredSchemaT | None:
        self.retry_times += 1
        raise ValueError("This function is unstable")

    @retry(
        retry_interval=0.01,
        max_retries=5,
        max_retry_interval=0.04,
        backoff_pattern="exponential",
    )
    async def generate_content_exponential(self) -> None:
        self.retry_times_exp += 1
        raise ValueError("This function is exponentially unstable")


class Greetings(BaseModel):
    greeting: str = "hello"


@pytest.mark.asyncio
async def test_retry_stable() -> None:
    llm = StableLLM(api_key="", model="")
    result = await llm.generate_content(Greetings, ChatHistory(messages=[]))
    assert llm.has_retried
    assert result is not None
    assert result.model_dump_json() == Greetings().model_dump_json()


@pytest.mark.asyncio
async def test_retry_unstable_linear() -> None:
    llm = UnstableLLM(api_key="", model="")
    start_time = time.time()
    with pytest.raises(ValueError, match="This function is unstable"):
        await llm.generate_content(Greetings, ChatHistory(messages=[]))
    end_time = time.time()
    assert llm.retry_times == 5
    total_time = end_time - start_time
    exp_time = (
        0.01 + 0.02 + 0.03 + 0.03
    )  # last failed attempt does not sleep, returns immediately
    assert total_time >= exp_time


@pytest.mark.asyncio
async def test_retry_unstable_exponential() -> None:
    llm = UnstableLLM(api_key="", model="")
    start_time = time.time()
    with pytest.raises(ValueError, match="This function is exponentially unstable"):
        await llm.generate_content_exponential()
    end_time = time.time()
    assert llm.retry_times_exp == 5
    total_time = end_time - start_time
    exp_time = (
        0.01 + 0.02 + 0.04 + 0.04
    )  # last failed attempt does not sleep, returns immediately
    assert total_time >= exp_time
