"""
schemas/message_schemas.py

Pydantic v2 request/response schemas for message endpoints.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Source citation ──────────────────────────────────────────────────────────

class SourceCitation(BaseModel):
    """One cited episode from the transcript knowledge base."""
    episode_slug: str
    guest: str
    title: str
    youtube_url: str
    timestamp: str | None = None   # e.g. "00:45:12"
    score: float | None = None     # retrieval similarity score


# ── Request schemas ──────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=32_000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("content must not be blank")
        return normalized


# ── Response schemas ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    sources: list[SourceCitation] | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]


# ── SSE event shapes ─────────────────────────────────────────────────────────

class SSETokenEvent(BaseModel):
    """Sent for each streamed token chunk."""
    type: Literal["token"] = "token"
    delta: str


class SSEDoneEvent(BaseModel):
    """Sent once when generation is complete."""
    type: Literal["done"] = "done"
    message_id: uuid.UUID
    sources: list[SourceCitation] | None = None
    artifact_id: uuid.UUID | None = None


class SSEErrorEvent(BaseModel):
    """Sent if an error occurs during streaming."""
    type: Literal["error"] = "error"
    code: str
    message: str
