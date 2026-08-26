"""
core/middleware.py

FastAPI middleware stack:
1. RequestIDMiddleware  — injects a unique X-Request-ID header into every request
   and response, and binds it to structlog's context so all log lines for that
   request include the same ID.
2. CORS — configured from settings.cors_origins_list.
"""

import uuid

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Adds a unique request_id to:
    - request.state.request_id   (for use in error bodies)
    - structlog context vars      (for log correlation)
    - X-Request-ID response header
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Bind to structlog so every log line in this request carries it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def register_middleware(app: FastAPI, cors_origins: list[str]) -> None:
    """Register all middleware on the FastAPI app. Call this in main.py."""
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
