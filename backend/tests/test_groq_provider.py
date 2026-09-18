"""GroqProvider tests — HTTP layer mocked, verifies request/response
handling against the real Groq (OpenAI-compatible) API shape, confirmed
live against api.groq.com on 2026-09-19."""

from unittest.mock import MagicMock, patch

from app.integrations.llm.groq_provider import GroqProvider


def _mock_response(content: str):
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    return mock


def test_complete_text_extracts_message_content():
    provider = GroqProvider()
    provider._api_key = "test-key"
    provider._model = "qwen/qwen3.8-27b"

    with patch("app.integrations.llm.groq_provider.httpx.post", return_value=_mock_response("Hello there.")) as mock_post:
        result = provider.complete_text("You are helpful.", "Say hi")

    assert result == "Hello there."
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.groq.com/openai/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert kwargs["json"]["model"] == "qwen/qwen3.8-27b"
    assert kwargs["json"]["messages"] == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Say hi"},
    ]
    assert "response_format" not in kwargs["json"]


def test_complete_json_sets_response_format():
    provider = GroqProvider()
    provider._api_key = "test-key"
    provider._model = "qwen/qwen3.8-27b"

    with patch("app.integrations.llm.groq_provider.httpx.post", return_value=_mock_response('{"intent": "FAILED_PAYMENT"}')) as mock_post:
        result = provider.complete_json("System.", "User message", '{"intent": "..."}')

    assert result == '{"intent": "FAILED_PAYMENT"}'
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["response_format"] == {"type": "json_object"}


def test_no_choices_raises():
    provider = GroqProvider()
    provider._api_key = "test-key"
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {"choices": []}

    with patch("app.integrations.llm.groq_provider.httpx.post", return_value=mock):
        try:
            provider.complete_text("sys", "user")
            assert False, "expected ValueError"
        except ValueError:
            pass
