from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/neuralgate"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Provider API keys — all optional, only providers with keys are used
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None

    # Embedding model for semantic cache
    embedding_model: str = "text-embedding-3-small"

    # Semantic cache settings
    cache_similarity_threshold: float = 0.95
    default_cache_ttl_hours: int = 24

    # Routing defaults
    default_requested_model: str = "auto"
    max_failover_attempts: int = 3

    class Config:
        env_file = ".env"


settings = Settings()


def get_available_providers() -> set[str]:
    available = set()
    if settings.anthropic_api_key:
        available.add("anthropic")
    if settings.openai_api_key:
        available.add("openai")
    if settings.google_api_key:
        available.add("google")
    if settings.xai_api_key:
        available.add("xai")
    if settings.deepseek_api_key:
        available.add("deepseek")
    if settings.mistral_api_key:
        available.add("mistral")
    return available
