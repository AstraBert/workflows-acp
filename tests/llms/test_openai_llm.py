import pytest
import time

from unittest.mock import patch, AsyncMock, PropertyMock
from openai import AsyncOpenAI
from openai.types.responses.parsed_response import (
    ParsedResponseOutputText,
    ParsedResponseOutputMessage,
    ParsedResponse,
)
from workflows_acp.constants import DEFAULT_OPENAI_MODEL, DEFAULT_MODEL
from workflows_acp.models import Action, Stop
from workflows_acp.llms.models import ChatHistory
from workflows_acp.llms.openai_llm import OpenAILLM


def test_openai_llm_init() -> None:
    llm = OpenAILLM(api_key="fake-api-key")
    assert llm.api_key == "fake-api-key"
    assert isinstance(llm._client, AsyncOpenAI)
    assert llm.model == DEFAULT_OPENAI_MODEL
    assert llm.model == DEFAULT_MODEL["openai"]


@pytest.mark.asyncio
async def test_openai_llm_generate() -> None:
    with patch.object(
        AsyncOpenAI, "responses", new_callable=PropertyMock
    ) as mock_responses:
        mock_parse = AsyncMock()
        content = Action(
            type="stop", tool_call=None, stop=Stop(stop_reason="", final_output="")
        ).model_dump_json()
        block = ParsedResponseOutputText[Action](
            text=content,
            type="output_text",
            parsed=Action.model_validate_json(content),
            annotations=[],
        )
        message = ParsedResponseOutputMessage[Action](
            id="1",
            content=[block],
            role="assistant",
            status="completed",
            type="message",
        )
        response = ParsedResponse(
            id="1",
            object="response",
            output=[message],
            parallel_tool_calls=False,
            tool_choice="none",
            tools=[],
            model="gpt-4.1",
            created_at=time.time(),
        )
        mock_parse.return_value = response
        mock_responses.return_value.parse = mock_parse
        llm = OpenAILLM(api_key="fake-api-key")
        response = await llm.generate_content(
            schema=Action, chat_history=ChatHistory(messages=[])
        )
        assert response is not None
        assert isinstance(response, Action)
        assert response.model_dump_json() == content
