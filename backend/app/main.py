"""
app/main.py

FastAPI application factory.
Responsible for:
  - Creating the FastAPI app instance
  - Registering middleware (CORS, request-ID)
  - Mounting all API routers
  - Application lifespan (startup/shutdown hooks for DB, logging)
  - Exception handler registration
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from core.errors import AppError, app_error_handler, generic_error_handler
from core.logging import configure_logging, get_logger
from core.middleware import register_middleware
from persistence.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: setup on startup, teardown on shutdown.
    Using the modern asynccontextmanager approach instead of deprecated events.
    """
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────────────────
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    logger.info(
        "app_startup",
        provider=settings.llm_provider.value,
        model=settings.active_model_name,
        environment=settings.app_env,
    )

    # Initialize DB connection pool
    init_db(settings.database_url)
    logger.info("startup_complete")

    yield  # Application is running

    # ── Shutdown ─────────────────────────────────────────────────────────────
    await close_db()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    Importing routers inside this function avoids circular imports.
    """
    settings = get_settings()

    app = FastAPI(
        title="The Lenny Growth Assistant — API",
        description=(
            "FastAPI backend for the Lenny Growth Assistant. "
            "Provides grounded Q&A, Ship30 essay generation, and artifact rendering "
            "powered by Claude Agent SDK + Qdrant RAG."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    register_middleware(app, settings.cors_origins_list)

    # ── Exception handlers ────────────────────────────────────────────────────
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    from api.routes_artifacts import router as artifacts_router
    from api.routes_health import router as health_router
    from api.routes_messages import router as messages_router
    from api.routes_sessions import router as sessions_router

    app.include_router(sessions_router, prefix="/api/v1")
    app.include_router(messages_router, prefix="/api/v1")
    app.include_router(artifacts_router, prefix="/api/v1")
    app.include_router(health_router)  # /health, /ready, /config, /admin — no prefix

    return app


# Module-level app instance (used by Uvicorn)
app = create_app()
