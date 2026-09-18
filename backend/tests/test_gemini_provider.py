"""GeminiProvider tests — HTTP layer mocked, verifies request/response
handling against the real Gemini REST API shape (confirmed live against
generativelanguage.googleapis.com on 2026-09-18)."""

from unittest.mock import MagicMock, patch

from app.integrations.llm.gemini_provider import GeminiProvider


def _mock_response(text: str):
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": text}], "role": "model"}, "finishReason": "STOP", "index": 0}],
        "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 19, "totalTokenCount": 27},
        "modelVersion": "gemini-flash-latest",
    }
    return mock


def test_complete_text_extracts_response_text():
    provider = GeminiProvider()
    provider._api_key = "test-key"
    provider._model = "gemini-flash-latest"

    with patch("app.integrations.llm.gemini_provider.httpx.post", return_value=_mock_response("Hello there.")) as mock_post:
        result = provider.complete_text("You are helpful.", "Say hi")

    assert result == "Hello there."
    args, kwargs = mock_post.call_args
    assert args[0] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
    assert kwargs["headers"]["X-goog-api-key"] == "test-key"
    assert kwargs["json"]["contents"][0]["parts"][0]["text"] == "Say hi"
    assert kwargs["json"]["systemInstruction"]["parts"][0]["text"] == "You are helpful."
    assert "generationConfig" not in kwargs["json"]


def test_complete_json_sets_response_mime_type():
    provider = GeminiProvider()
    provider._api_key = "test-key"
    provider._model = "gemini-flash-latest"

    with patch("app.integrations.llm.gemini_provider.httpx.post", return_value=_mock_response('{"intent": "FAILED_PAYMENT"}')) as mock_post:
        result = provider.complete_json("System.", "User message", '{"intent": "..."}')

    assert result == '{"intent": "FAILED_PAYMENT"}'
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["generationConfig"]["responseMimeType"] == "application/json"


def test_no_candidates_raises():
    provider = GeminiProvider()
    provider._api_key = "test-key"
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {"candidates": []}

    with patch("app.integrations.llm.gemini_provider.httpx.post", return_value=mock):
        try:
            provider.complete_text("sys", "user")
            assert False, "expected ValueError"
        except ValueError:
            pass
