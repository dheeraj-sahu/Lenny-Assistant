"""
app/config.py

Single source of truth for all runtime configuration.
Values are read from environment variables (or .env file) exactly once at startup.
No other module should import os.environ directly — always import from here.
"""

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"


class Settings(BaseSettings):
    """
    All configuration is loaded from environment variables.
    Required fields have no default; optional ones do.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin
            for origin in (item.strip() for item in self.cors_origins.split(","))
            if origin
        ]

    # ── LLM Provider ────────────────────────────────────────────
    llm_provider: LLMProvider = LLMProvider.OLLAMA

    # Ollama settings
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"

    # Anthropic Cloud settings (optional)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    @model_validator(mode="after")
    def validate_provider_config(self) -> "Settings":
        """Warn (don't crash) if Anthropic is selected but key is missing."""
        if self.llm_provider == LLMProvider.ANTHROPIC and not self.anthropic_api_key:
            import warnings
            warnings.warn(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. "
                "Requests will fail. Set the key or switch to LLM_PROVIDER=ollama.",
                stacklevel=2,
            )
        return self

    # ── Database ────────────────────────────────────────────────
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "lenny_assistant"
    postgres_user: str = "lenny"
    postgres_password: str = "changeme"
    database_url: str = ""

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return self

    # ── Qdrant ──────────────────────────────────────────────────
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "lenny_transcripts"

    # ── Embedding Model ─────────────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"

    # ── Ingestion ───────────────────────────────────────────────
    transcripts_repo_url: str = "https://github.com/ChatPRD/lennys-podcast-transcripts.git"
    transcripts_local_path: str = "/app/data/transcripts"

    # Retrieval tuning
    retrieval_top_k: int = 8
    retrieval_score_threshold: float = 0.35  # min cosine similarity to return a chunk

    # ── Security ────────────────────────────────────────────────
    admin_secret: str = "changeme-admin-secret"

    # ── Computed helpers ─────────────────────────────────────────
    @property
    def active_model_name(self) -> str:
        """Human-readable model name for the /config endpoint and UI badge."""
        if self.llm_provider == LLMProvider.OLLAMA:
            return self.ollama_model
        return self.anthropic_model

    @property
    def active_provider_label(self) -> str:
        """UI-facing label: 'Local · Ollama · llama3.1:8b' or 'Cloud · Claude'."""
        if self.llm_provider == LLMProvider.OLLAMA:
            return f"Local · Ollama · {self.ollama_model}"
        return f"Cloud · Claude · {self.anthropic_model}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached singleton Settings instance.
    Use this everywhere instead of constructing Settings() directly.
    """
    return Settings()
