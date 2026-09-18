"""Gemini provider — plain REST via httpx (no google-genai SDK dependency,
consistent with the rest of this codebase's lean-dependency approach; see
CogneeMemoryService for the same reasoning). Implements the same
LLMProvider interface as AnthropicProvider — application code never
branches on which provider is active.
"""

import logging
import time

import httpx

from app.config import get_settings
from app.integrations.llm.base import LLMProvider

settings = get_settings()
logger = logging.getLogger("nishchint.gemini")

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Gemini's 503 error body literally says "Spikes in demand are usually
# temporary. Please try again later." — a short retry directly follows that
# guidance. Kept small: LLMService already has its own fallback-to-template
# path for when even retries don't help, so this isn't the last line of
# defense, just cheap resilience for genuinely transient spikes.
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.5


class GeminiProvider(LLMProvider):
    def __init__(self):
        self._api_key = settings.llm_api_key
        self._model = settings.llm_model or "gemini-flash-latest"

    def _generate(self, system_prompt: str, user_prompt: str, response_mime_type: str | None = None) -> str:
        payload = {
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
        }
        if response_mime_type:
            payload["generationConfig"] = {"responseMimeType": response_mime_type}

        last_exc: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = httpx.post(
                    f"{API_BASE}/{self._model}:generateContent",
                    headers={"Content-Type": "application/json", "X-goog-api-key": self._api_key},
                    json=payload,
                    timeout=30.0,
                )
                if resp.status_code == 503 and attempt < MAX_ATTEMPTS:
                    logger.warning("Gemini 503 (high demand), retrying (%s/%s)", attempt, MAX_ATTEMPTS)
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    raise ValueError(f"Gemini returned no candidates: {data}")
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts).strip()
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code != 503 or attempt >= MAX_ATTEMPTS:
                    raise

        raise last_exc or RuntimeError("Gemini request failed after retries")

    def complete_json(self, system_prompt: str, user_prompt: str, schema_hint: str) -> str:
        full_system = f"{system_prompt}\n\nRespond ONLY with JSON matching this shape, no prose:\n{schema_hint}"
        return self._generate(full_system, user_prompt, response_mime_type="application/json")

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        return self._generate(system_prompt, user_prompt)
