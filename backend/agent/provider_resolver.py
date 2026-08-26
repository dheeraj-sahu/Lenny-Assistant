"""
agent/provider_resolver.py

Constructs the Anthropic SDK client pointed at the correct backend:
  - Ollama (default): ANTHROPIC_BASE_URL=http://ollama:11434, dummy auth token
  - Anthropic Cloud: real ANTHROPIC_API_KEY, no base_url override

This is the ONLY place in the codebase that knows which provider is active.
All other components (orchestrator, tools) use the resolved client object
without ever branching on provider name — this is what makes the swap code-free.
"""

import anthropic

from app.config import LLMProvider, Settings, get_settings
from core.logging import get_logger

logger = get_logger(__name__)


def build_anthropic_client(settings: Settings | None = None) -> anthropic.Anthropic:
    """
    Build and return an Anthropic SDK client configured for the active provider.

    The same client type works for both Ollama and Anthropic Cloud because Ollama
    exposes an Anthropic-compatible /v1/messages endpoint.
    """
    cfg = settings or get_settings()

    if cfg.llm_provider == LLMProvider.OLLAMA:
        logger.info(
            "provider_resolved",
            provider="ollama",
            base_url=cfg.ollama_base_url,
            model=cfg.ollama_model,
        )
        return anthropic.Anthropic(
            base_url=cfg.ollama_base_url,
            api_key="ollama",  # Ollama ignores the key but the SDK requires a non-empty value
        )
    else:
        if not cfg.anthropic_api_key:
            raise ValueError(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. "
                "Set the key or switch to LLM_PROVIDER=ollama."
            )
        logger.info(
            "provider_resolved",
            provider="anthropic",
            model=cfg.anthropic_model,
        )
        return anthropic.Anthropic(api_key=cfg.anthropic_api_key)


def get_active_model(settings: Settings | None = None) -> str:
    """Return the model name string for the current provider."""
    cfg = settings or get_settings()
    if cfg.llm_provider == LLMProvider.OLLAMA:
        return cfg.ollama_model
    return cfg.anthropic_model
