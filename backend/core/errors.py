"""
core/errors.py

Centralised exception hierarchy and FastAPI exception handlers.
All internal errors map to structured JSON error bodies with stable error codes
so callers (and log aggregators) can distinguish error categories without parsing
free-form strings.

Error body shape:
{
    "error": {
        "code": "RETRIEVAL_TIMEOUT",
        "message": "Human-readable description",
        "request_id": "uuid"
    }
}
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from core.logging import get_logger

logger = get_logger(__name__)


# ── Base application exception ──────────────────────────────────────────────

class AppError(Exception):
    """Base class for all application-specific errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ── Domain-specific exceptions ──────────────────────────────────────────────

class SessionNotFoundError(AppError):
    status_code = 404
    error_code = "SESSION_NOT_FOUND"


class ArtifactNotFoundError(AppError):
    status_code = 404
    error_code = "ARTIFACT_NOT_FOUND"


class ModelUnavailableError(AppError):
    status_code = 503
    error_code = "MODEL_UNAVAILABLE"


class ModelTimeoutError(AppError):
    status_code = 504
    error_code = "MODEL_TIMEOUT"


class RetrievalError(AppError):
    status_code = 502
    error_code = "RETRIEVAL_ERROR"


class RetrievalTimeoutError(AppError):
    status_code = 504
    error_code = "RETRIEVAL_TIMEOUT"


class DatabaseError(AppError):
    status_code = 503
    error_code = "DATABASE_ERROR"


class SanitizationError(AppError):
    status_code = 422
    error_code = "SANITIZATION_ERROR"


class IngestionError(AppError):
    status_code = 500
    error_code = "INGESTION_ERROR"


class AdminAuthError(AppError):
    status_code = 401
    error_code = "UNAUTHORIZED"


# ── FastAPI exception handlers ───────────────────────────────────────────────

def _error_body(request: Request, code: str, message: str) -> dict:
    request_id = getattr(request.state, "request_id", "unknown")
    return {"error": {"code": code, "message": message, "request_id": request_id}}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.error(
        "application_error",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(request, exc.error_code, exc.message),
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        exc_type=type(exc).__name__,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=500,
        content=_error_body(request, "INTERNAL_ERROR", "An unexpected error occurred."),
    )
