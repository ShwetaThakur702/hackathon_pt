"""Voice input endpoint (spec section 48). Speech-to-text only — never
authoritative for anything: the transcribed text goes into /chat exactly
like typed text, running through the same understanding/verification
pipeline. Voice never blocks the core loop; a transcription failure here
just means the customer types instead, nothing else in the app degrades.
"""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.integrations.whisper.voice_service import voice_service

logger = logging.getLogger("nishchint.voice")

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")
    try:
        return voice_service.transcribe(audio_bytes, filename_hint=file.filename or "audio.webm")
    except Exception as exc:
        logger.exception("Voice transcription failed")
        raise HTTPException(status_code=503, detail=f"Voice transcription unavailable right now: {exc}") from exc
