"""
schemas/session_schemas.py

Pydantic v2 request/response schemas for session endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ── Request schemas ──────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    """Body is optional — sessions can be created with no initial data."""
    title: str | None = Field(None, max_length=512, description="Optional pre-set title")

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank")
        return normalized


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
