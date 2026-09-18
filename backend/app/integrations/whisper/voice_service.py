"""VoiceService — multilingual speech-to-text via local Whisper (spec
section 48).

Swapped in for the original Sarvam plan on explicit product direction:
needed genuinely multilingual support (not just Hindi/English), and a
locally-run model means no extra paid API dependency for voice input —
Whisper's multilingual checkpoints cover ~99 languages including Hindi,
Hinglish code-switching, and English in the same utterance.

Text-to-speech (`synthesize`) is intentionally out of scope here — Whisper
is speech-to-text only, and voice *output* was not part of this ask; it
stays a NotImplementedError stub, same as the abstraction it replaces.

Voice must never block the core autonomous workflow (unchanged constraint):
the model loads lazily on first use (not at import/startup), and any
failure raises a plain exception the API layer turns into a clean 503
rather than crashing the app.
"""

from __future__ import annotations

import logging
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger("nishchint.whisper")


class VoiceService(ABC):
    @abstractmethod
    def transcribe(self, audio: bytes, filename_hint: str = "audio.webm") -> dict: ...

    @abstractmethod
    def synthesize(self, text: str, language: str) -> bytes: ...


class WhisperVoiceService(VoiceService):
    """Local, multilingual transcription via faster-whisper. No external
    API key required — runs fully offline once model weights are cached."""

    def __init__(self):
        self._model = None  # lazy-loaded so importing this module never
        # triggers a multi-hundred-MB model download (matters for app
        # startup time and for the test suite, which never touches this).

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            settings = get_settings()
            logger.info(
                "Loading Whisper model '%s' (first use — downloads/caches weights if not already local)...",
                settings.whisper_model_size,
            )
            self._model = WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, audio: bytes, filename_hint: str = "audio.webm") -> dict:
        """Returns {"text", "language", "language_probability"}. Language
        is auto-detected per-utterance by Whisper — never assumed."""
        model = self._get_model()
        suffix = Path(filename_hint).suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(audio)
            tmp.flush()
            segments, info = model.transcribe(tmp.name, vad_filter=True)
            text = " ".join(segment.text.strip() for segment in segments).strip()
        return {
            "text": text,
            "language": info.language,
            "language_probability": round(float(info.language_probability), 3),
        }

    def synthesize(self, text: str, language: str) -> bytes:
        raise NotImplementedError("Voice output (text-to-speech) is not implemented in this prototype.")


voice_service: VoiceService = WhisperVoiceService()
