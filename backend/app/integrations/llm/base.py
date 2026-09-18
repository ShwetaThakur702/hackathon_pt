from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Provider-specific code must live entirely behind this interface —
    application logic (agent nodes) never imports a provider SDK directly."""

    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str, schema_hint: str) -> str:
        """Return a raw JSON string matching schema_hint (best effort)."""

    @abstractmethod
    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        """Return free-form natural-language text."""
