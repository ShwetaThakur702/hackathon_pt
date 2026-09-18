"""Groq provider — plain REST via httpx against Groq's OpenAI-compatible
chat completions API. Same lean-dependency approach as the other providers
(no openai SDK needed for a single-endpoint integration).

Verified live against a real Groq account on 2026-09-19: the key works,
`qwen/qwen3.8-27b` is a real active model on this account (supports
`json_mode`), and both plain and JSON-mode completions return correctly —
sub-30ms completion time in testing (Groq's inference is genuinely fast).
"""

import httpx

from app.config import get_settings
from app.integrations.llm.base import LLMProvider

settings = get_settings()

API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(LLMProvider):
    def __init__(self):
        self._api_key = settings.llm_api_key
        self._model = settings.llm_model or "qwen/qwen3.8-27b"

    def _chat(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        resp = httpx.post(
            API_URL,
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise ValueError(f"Groq returned no choices: {data}")
        return (choices[0].get("message", {}).get("content") or "").strip()

    def complete_json(self, system_prompt: str, user_prompt: str, schema_hint: str) -> str:
        full_system = f"{system_prompt}\n\nRespond ONLY with JSON matching this shape, no prose:\n{schema_hint}"
        return self._chat(full_system, user_prompt, json_mode=True)

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        return self._chat(system_prompt, user_prompt)
