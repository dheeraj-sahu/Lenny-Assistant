"""
api/routes_sessions.py

Session CRUD endpoints:
  POST   /sessions             — create a new chat session
  GET    /sessions             — list all sessions
  GET    /sessions/{id}        — get one session
  DELETE /sessions/{id}        — delete a session
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from core.errors import SessionNotFoundError
from persistence.database import get_db
from persistence.repositories.session_repository import SessionRepository
from schemas.session_schemas import (
    CreateSessionRequest,
    SessionListResponse,
    SessionResponse,
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: CreateSessionRequest = CreateSessionRequest(),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Create a new independent chat session."""
    settings = get_settings()
    repo = SessionRepository(db)
    session = await repo.create(active_provider=settings.llm_provider.value)
    if body.title:
        await repo.set_title(session.id, body.title)
        session.title = body.title
    return SessionResponse.model_validate(session)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """List all sessions, newest first."""
    repo = SessionRepository(db)
    sessions = await repo.list_all(limit=limit, offset=offset)
    return SessionListResponse(
        sessions=[SessionResponse.model_validate(s) for s in sessions],
        total=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Fetch a single session by ID."""
    repo = SessionRepository(db)
    session = await repo.get_by_id(session_id)
    if not session:
        raise SessionNotFoundError(f"Session {session_id} not found")
    return SessionResponse.model_validate(session)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a session and all its messages and artifacts (cascade)."""
    repo = SessionRepository(db)
    deleted = await repo.delete(session_id)
    if not deleted:
        raise SessionNotFoundError(f"Session {session_id} not found")
