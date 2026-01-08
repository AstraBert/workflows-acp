import pytest

from unittest.mock import patch, AsyncMock, PropertyMock
from google.genai import Client as GenAIClient
from google.genai.types import GenerateContentResponse, Content, Part, Candidate
from workflows_acp.constants import DEFAULT_GOOGLE_MODEL, DEFAULT_MODEL
from workflows_acp.models import Action, Stop
from workflows_acp.llms.models import ChatHistory
from workflows_acp.llms.google_llm import GoogleLLM


def test_google_llm_init() -> None:
    llm = GoogleLLM(api_key="fake-api-key")
    assert llm.api_key == "fake-api-key"
    assert isinstance(llm._client, GenAIClient)
    assert llm.model == DEFAULT_GOOGLE_MODEL
    assert llm.model == DEFAULT_MODEL["google"]


@pytest.mark.asyncio
async def test_google_llm_generate() -> None:
    with patch.object(GenAIClient, "aio", new_callable=PropertyMock) as mock_aio:
        mock_generate = AsyncMock()
        content = Action(
            type="stop", tool_call=None, stop=Stop(stop_reason="", final_output="")
        ).model_dump_json()
        mock_generate.return_value = GenerateContentResponse(
            candidates=[
                Candidate(
                    content=Content(
                        role="assistant", parts=[Part.from_text(text=content)]
                    )
                )
            ]
        )
        mock_aio.return_value.models.generate_content = mock_generate

        llm = GoogleLLM(api_key="fake-api-key")
        response = await llm.generate_content(
            schema=Action, chat_history=ChatHistory(messages=[])
        )
        assert response is not None
        assert isinstance(response, Action)
        assert response.model_dump_json() == content
