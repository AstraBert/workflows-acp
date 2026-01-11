from google.genai.types import Content, Part
from workflows_acp.llms.models import ChatHistory, ChatMessage


def test_chat_message_conversion() -> None:
    message = ChatMessage(role="user", content="hello world")
    google_message = message.to_google_message()
    assert isinstance(google_message, Content)
    assert google_message.role == message.role
    assert isinstance(google_message.parts, list)
    assert len(google_message.parts) == 1
    assert google_message.parts[0].text == message.content
    ant_message = message.to_anthropic_message()
    assert isinstance(ant_message, dict)
    assert ant_message["content"] == message.content
    assert ant_message["role"] == message.role
    message.role = "system"
    ant_message = message.to_anthropic_message()
    assert isinstance(ant_message, str)
    assert ant_message == message.content
    google_message = message.to_google_message()
    assert isinstance(google_message, Part)
    assert google_message.text == message.content
    message.role = "user"
    openai_message = message.to_openai_message()
    assert isinstance(openai_message, dict)
    assert openai_message["content"] == message.content
    assert openai_message["role"] == message.role
    assert openai_message.get("type") == "message"


def test_chat_history() -> None:
    messages = [
        ChatMessage(role="system", content="say hello"),
        ChatMessage(role="user", content="hi"),
    ]
    chat_history = ChatHistory(messages=messages)
    chat_history.append(ChatMessage(role="assistant", content="hello"))
    assert len(chat_history.messages) == 3
    assert chat_history.messages[2].role == "assistant"
    assert chat_history.messages[2].content == "hello"
    system_prompt, google_chat_history = chat_history.to_google_message_history()
    assert isinstance(google_chat_history, list)
    assert len(google_chat_history) == len(chat_history.messages) - 1
    for i, google_msg in enumerate(google_chat_history):
        if chat_history.messages[i + 1].role == "user":
            assert google_msg.role == chat_history.messages[i + 1].role
        else:
            assert google_msg.role == "model"
        assert isinstance(google_msg.parts, list)
        assert len(google_msg.parts) == 1
        assert google_msg.parts[0].text == chat_history.messages[i + 1].content
    assert isinstance(system_prompt, list)
    assert len(system_prompt) == 1
    assert isinstance(system_prompt[0], Part)
    assert system_prompt[0].text == messages[0].content
    system, ant_chat_history = chat_history.to_anthropic_message_history()
    assert isinstance(system, str)
    assert system == chat_history.messages[0].content
    assert len(ant_chat_history) == (len(chat_history.messages) - 1)
    for i, ant_msg in enumerate(ant_chat_history):
        assert ant_msg["role"] == chat_history.messages[i + 1].role
        assert ant_msg["content"] == chat_history.messages[i + 1].content
    openai_chat_history = chat_history.to_openai_message_history()
    assert len(openai_chat_history) == len(chat_history.messages)
    for i, openai_msg in enumerate(openai_chat_history):
        assert openai_msg["role"] == chat_history.messages[i].role
        assert openai_msg["content"] == chat_history.messages[i].content
        assert openai_msg.get("type") == "message"
