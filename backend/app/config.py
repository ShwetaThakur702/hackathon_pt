from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "anthropic"
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-5"

    # Voice input — local, multilingual speech-to-text via faster-whisper
    # (see app/integrations/whisper/voice_service.py). Runs fully offline,
    # no API key needed. tiny|base|small|medium|large-v3 — small is a
    # reasonable accuracy/speed tradeoff for Hindi/Hinglish code-switching
    # on CPU; bump to medium/large-v3 if you have the compute and want
    # better accuracy.
    whisper_model_size: str = "small"

    # Cognee Cloud — semantic/contextual memory layer (see
    # app/integrations/cognee/cognee_memory_service.py). NOT the source of
    # truth for any financial/transactional fact; the database remains
    # authoritative for that. cognee_base_url is the per-tenant Cloud URL,
    # e.g. https://your-tenant.aws.cognee.ai (see docs.cognee.ai).
    cognee_enabled: bool = True
    cognee_api_key: str = ""
    cognee_base_url: str = ""
    cognee_dataset: str = "nishchint_memory"
    cognee_search_type: str = "GRAPH_COMPLETION"
    cognee_top_k: int = 5

    database_url: str = "sqlite:///./nishchint.db"

    n8n_base_url: str = ""
    n8n_webhook_url: str = ""
    n8n_api_key: str = ""
    n8n_callback_secret: str = "change-me"

    app_env: str = "development"
    simulation_mode: bool = True
    high_value_threshold: int = 50000
    backend_base_url: str = "http://localhost:8000"
    # Comma-separated list, or "*" for dev. Deployable environments should
    # set this to the real frontend origin(s) — never assume localhost.
    cors_allow_origins: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_allow_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def cognee_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.cognee_enabled and settings.cognee_api_key and settings.cognee_base_url)
