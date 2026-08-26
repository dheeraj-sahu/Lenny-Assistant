"""
api/routes_health.py

Operational endpoints:
  GET /health       — overall health summary (200 = all green, 503 = degraded)
  GET /ready        — k8s/docker readiness probe (only checks DB)
  GET /config       — read-only view of active config (no secrets)
  POST /config/provider — switch the active LLM provider at runtime

  POST /admin/refresh-kb  — trigger a knowledge-base ingestion run (admin-protected)
"""

import asyncio
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.config import get_settings, LLMProvider
from core.logging import get_logger
from persistence.database import get_engine

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)

# ── Runtime provider override (in-memory, resets on container restart) ─────────
# This lets the user switch providers from the UI without restarting the server.
_runtime_provider_override: LLMProvider | None = None
_runtime_api_key: str | None = None  # user-supplied Anthropic key (session only)


def get_effective_provider() -> LLMProvider:
    """Return the runtime-overridden provider, or the one from config."""
    if _runtime_provider_override is not None:
        return _runtime_provider_override
    return get_settings().llm_provider


def get_effective_api_key() -> str:
    """Return the user-supplied runtime API key, or the one from config."""
    if _runtime_api_key:
        return _runtime_api_key
    return get_settings().anthropic_api_key


# ── helpers ──────────────────────────────────────────────────────────────────

async def _check_db() -> dict[str, Any]:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        logger.error("health_db_fail", error=str(exc))
        return {"status": "down", "error": str(exc)}


async def _check_qdrant() -> dict[str, Any]:
    settings = get_settings()
    url = f"http://{settings.qdrant_host}:{settings.qdrant_port}/healthz"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return {"status": "ok"}
            return {"status": "degraded", "http_status": resp.status_code}
    except Exception as exc:
        logger.warning("health_qdrant_fail", error=str(exc))
        return {"status": "down", "error": str(exc)}


async def _check_ollama() -> dict[str, Any]:
    settings = get_settings()
    effective = get_effective_provider()
    if effective != LLMProvider.OLLAMA:
        return {"status": "skipped", "reason": "provider=anthropic"}
    url = f"{settings.ollama_base_url}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return {"status": "ok"}
            return {"status": "degraded", "http_status": resp.status_code}
    except Exception as exc:
        logger.warning("health_ollama_fail", error=str(exc))
        return {"status": "down", "error": str(exc)}


async def _get_corpus_info() -> dict[str, Any]:
    """Fetch latest ingestion run info from the DB for the /config endpoint."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT corpus_commit_sha, chunk_count FROM ingestion_runs "
                    "WHERE status = 'completed' ORDER BY finished_at DESC LIMIT 1"
                )
            )
            row = result.fetchone()
            if row:
                return {"corpus_version": row[0], "chunk_count": row[1]}
    except Exception:
        pass
    return {}


# ── endpoints ────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Returns the status of each dependency independently so a partial outage
    (e.g. Qdrant down but Ollama up) is diagnosable rather than a generic 503.
    """
    db_status, qdrant_status, ollama_status = await asyncio.gather(
        _check_db(), _check_qdrant(), _check_ollama()
    )

    all_ok = all(
        s.get("status") in ("ok", "skipped")
        for s in [db_status, qdrant_status, ollama_status]
    )

    return {
        "status": "healthy" if all_ok else "degraded",
        "components": {
            "database": db_status,
            "qdrant": qdrant_status,
            "ollama": ollama_status,
        },
    }


@router.get("/ready")
async def readiness_probe() -> dict[str, str]:
    """Minimal readiness probe — only checks DB (required for request handling)."""
    db_status = await _check_db()
    if db_status["status"] != "ok":
        raise HTTPException(status_code=503, detail="Database not ready")
    return {"status": "ready"}


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """
    Exposes the active runtime configuration (read-only, no secrets).
    The frontend reads this to display the provider badge and model info.
    Includes corpus version and chunk count from the last successful ingestion run.
    """
    settings = get_settings()
    effective = get_effective_provider()

    # Determine labels based on effective provider (may differ from settings if overridden)
    if effective == LLMProvider.OLLAMA:
        model = settings.ollama_model
        label = f"Local · Ollama · {settings.ollama_model}"
    else:
        model = settings.anthropic_model
        label = f"Cloud · Claude · {settings.anthropic_model}"

    corpus = await _get_corpus_info()

    return {
        "provider": effective.value,
        "model": model,
        "provider_label": label,
        "embedding_model": settings.embedding_model,
        "qdrant_collection": settings.qdrant_collection,
        "environment": settings.app_env,
        "ollama_model": settings.ollama_model,
        "anthropic_model": settings.anthropic_model,
        **corpus,
    }


class ProviderSwitchRequest(BaseModel):
    provider: str               # "ollama" | "anthropic"
    api_key: str | None = None  # user-supplied Anthropic API key (optional)


@router.post("/config/provider")
async def switch_provider(body: ProviderSwitchRequest) -> dict[str, Any]:
    """
    Switch the active LLM provider at runtime without restarting the server.
    The switch is in-memory only — it resets when the container restarts.
    To make it permanent, update LLM_PROVIDER in .env and restart.
    """
    global _runtime_provider_override, _runtime_api_key

    if body.provider not in ("ollama", "anthropic"):
        raise HTTPException(status_code=400, detail="provider must be 'ollama' or 'anthropic'")

    settings = get_settings()
    if body.provider == "anthropic":
        # Accept user-supplied key OR fall back to .env key
        effective_key = body.api_key or settings.anthropic_api_key
        if not effective_key:
            raise HTTPException(
                status_code=400,
                detail="Anthropic API key required. Enter your key in the provider switcher.",
            )
        _runtime_api_key = effective_key  # store for agent use
    else:
        _runtime_api_key = None  # clear when switching back to Ollama

    _runtime_provider_override = LLMProvider(body.provider)
    logger.info("provider_switched", new_provider=body.provider, key_source="user" if body.api_key else "env")

    # Return the new effective config (same shape as GET /config)
    return await get_config()


@router.post("/admin/refresh-kb", status_code=202)
async def refresh_knowledge_base(
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
) -> dict[str, str]:
    """
    Trigger a full ingestion pipeline run in the background.
    Protected by the ADMIN_SECRET header — not user-facing.
    """
    settings = get_settings()
    if x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=401, detail="Invalid admin secret")

    # Import here to avoid circular imports; ingestion is heavy
    from ingestion.ingest_pipeline import run_ingestion_pipeline
    import asyncio

    # Fire and forget — the run is tracked in the ingestion_runs table
    asyncio.create_task(run_ingestion_pipeline())

    return {"status": "accepted", "message": "Ingestion pipeline started in background"}
