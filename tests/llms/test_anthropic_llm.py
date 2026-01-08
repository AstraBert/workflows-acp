import pytest

from unittest.mock import patch, AsyncMock, PropertyMock
from anthropic import AsyncAnthropic
from anthropic.types.beta.parsed_beta_message import (
    ParsedBetaMessage,
    ParsedBetaTextBlock,
)
from anthropic.types.beta.beta_usage import BetaUsage
from workflows_acp.constants import DEFAULT_ANTHROPIC_MODEL, DEFAULT_MODEL
from workflows_acp.models import Action, Stop
from workflows_acp.llms.models import ChatHistory
from workflows_acp.llms.anthropic_llm import AnthropicLLM


def test_anthropic_llm_init() -> None:
    llm = AnthropicLLM(api_key="fake-api-key")
    assert llm.api_key == "fake-api-key"
    assert isinstance(llm._client, AsyncAnthropic)
    assert llm.model == DEFAULT_ANTHROPIC_MODEL
    assert llm.model == DEFAULT_MODEL["anthropic"]


@pytest.mark.asyncio
async def test_anthropic_llm_generate() -> None:
    with patch.object(AsyncAnthropic, "beta", new_callable=PropertyMock) as mock_beta:
        mock_parse = AsyncMock()
        content = Action(
            type="stop", tool_call=None, stop=Stop(stop_reason="", final_output="")
        ).model_dump_json()
        block = ParsedBetaTextBlock[Action](
            text=content, type="text", parsed_output=Action.model_validate_json(content)
        )
        response = ParsedBetaMessage[Action](
            content=[block],
            model="claude-haiku-4-5",
            role="assistant",
            type="message",
            usage=BetaUsage(input_tokens=0, output_tokens=0),
            id="1",
        )
        mock_parse.return_value = response
        mock_beta.return_value.messages.parse = mock_parse

        llm = AnthropicLLM(api_key="fake-api-key")
        response = await llm.generate_content(
            schema=Action, chat_history=ChatHistory(messages=[])
        )
        assert response is not None
        assert isinstance(response, Action)
        assert response.model_dump_json() == content
