"""WhisperVoiceService / /api/voice/transcribe tests. The real model is
never loaded here — faster-whisper's WhisperModel is mocked, same
discipline as the Cognee/n8n/Gemini HTTP mocks (no heavyweight model
download during `pytest`)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.integrations.whisper.voice_service import WhisperVoiceService


def _mock_model(text: str, language: str = "hi", language_probability: float = 0.97):
    segment = SimpleNamespace(text=text)
    info = SimpleNamespace(language=language, language_probability=language_probability)
    model = MagicMock()
    model.transcribe.return_value = ([segment], info)
    return model


def test_transcribe_returns_text_and_detected_language():
    service = WhisperVoiceService()
    service._model = _mock_model(" Mere paise nahi aaye ")

    result = service.transcribe(b"fake-audio-bytes", filename_hint="clip.webm")

    assert result["text"] == "Mere paise nahi aaye"
    assert result["language"] == "hi"
    assert result["language_probability"] == 0.97


def test_transcribe_joins_multiple_segments():
    service = WhisperVoiceService()
    seg1 = SimpleNamespace(text="Mere paise")
    seg2 = SimpleNamespace(text="nahi aaye")
    info = SimpleNamespace(language="hi", language_probability=0.9)
    model = MagicMock()
    model.transcribe.return_value = ([seg1, seg2], info)
    service._model = model

    result = service.transcribe(b"fake-audio-bytes")
    assert result["text"] == "Mere paise nahi aaye"


def test_model_loads_lazily_only_on_first_transcribe():
    service = WhisperVoiceService()
    assert service._model is None

    with patch("faster_whisper.WhisperModel", return_value=_mock_model("hello")) as mock_cls:
        service.transcribe(b"fake-audio-bytes")

    mock_cls.assert_called_once()
    assert service._model is not None


def test_transcribe_endpoint_returns_json(client):
    with patch(
        "app.api.voice.voice_service.transcribe",
        return_value={"text": "Abhi tak paise nahi aaye", "language": "hi", "language_probability": 0.95},
    ):
        resp = client.post("/api/voice/transcribe", files={"file": ("clip.webm", b"fake-bytes", "audio/webm")})

    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "Abhi tak paise nahi aaye"
    assert body["language"] == "hi"


def test_transcribe_endpoint_rejects_empty_file(client):
    resp = client.post("/api/voice/transcribe", files={"file": ("clip.webm", b"", "audio/webm")})
    assert resp.status_code == 400


def test_transcribe_endpoint_returns_503_on_failure(client):
    with patch("app.api.voice.voice_service.transcribe", side_effect=RuntimeError("model unavailable")):
        resp = client.post("/api/voice/transcribe", files={"file": ("clip.webm", b"fake-bytes", "audio/webm")})
    assert resp.status_code == 503
