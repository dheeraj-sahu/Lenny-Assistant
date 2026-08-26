"""
schemas/session_schemas.py

Pydantic v2 request/response schemas for session endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Request schemas ──────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    """Body is optional — sessions can be created with no initial data."""
    title: str | None = Field(None, max_length=512, description="Optional pre-set title")


# ── Response schemas ─────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    active_provider: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int
