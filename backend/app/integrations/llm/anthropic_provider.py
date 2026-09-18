import anthropic

from app.config import get_settings
from app.integrations.llm.base import LLMProvider

settings = get_settings()


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.llm_api_key)
        self._model = settings.llm_model

    def complete_json(self, system_prompt: str, user_prompt: str, schema_hint: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=f"{system_prompt}\n\nRespond ONLY with JSON matching this shape, no prose:\n{schema_hint}",
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
