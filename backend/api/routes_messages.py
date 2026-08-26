"""
api/routes_messages.py

Message endpoints for a session:
  GET  /sessions/{id}/messages          — list conversation history
  POST /sessions/{id}/messages/stream   — send a message, get SSE stream back

The stream endpoint:
1. Persists the user message immediately.
2. Hands off to the Agent Orchestrator.
3. Yields SSE events: token deltas → done (with sources + artifact_id) | error.
"""

import json
import time
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agent.orchestrator import AgentOrchestrator
from core.errors import SessionNotFoundError
from core.logging import get_logger
from persistence.database import get_db
from persistence.repositories.message_repository import MessageRepository
from persistence.repositories.session_repository import SessionRepository
from schemas.message_schemas import (
    MessageListResponse,
    MessageResponse,
    SSEDoneEvent,
    SSEErrorEvent,
    SSETokenEvent,
    SendMessageRequest,
)

router = APIRouter(prefix="/sessions/{session_id}/messages", tags=["Messages"])
logger = get_logger(__name__)


def _sse(event_obj) -> str:
    """Serialize a Pydantic model as an SSE data line."""
    return f"data: {event_obj.model_dump_json()}\n\n"


@router.get("", response_model=MessageListResponse)
async def list_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    """Return the full message history for a session."""
    session_repo = SessionRepository(db)
    if not await session_repo.get_by_id(session_id):
        raise SessionNotFoundError(f"Session {session_id} not found")

    msg_repo = MessageRepository(db)
    messages = await msg_repo.list_by_session(session_id)
    return MessageListResponse(
        messages=[MessageResponse.model_validate(m) for m in messages]
    )


@router.post("/stream")
async def stream_message(
    session_id: uuid.UUID,
    body: SendMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    POST a user message, get a streaming SSE response.

    SSE event types:
      {"type": "token",  "delta": "..."}          — streamed token
      {"type": "done",   "message_id": "...", "sources": [...], "artifact_id": "..."}
      {"type": "error",  "code": "...", "message": "..."}
    """
    # 1. Validate session exists
    session_repo = SessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise SessionNotFoundError(f"Session {session_id} not found")

    # 2. Persist user message
    msg_repo = MessageRepository(db)
    user_msg = await msg_repo.create(
        session_id=session_id,
        role="user",
        content=body.content,
    )
    await db.commit()

    # 3. Auto-set session title from first user message
    if not session.title:
        title = body.content[:80].strip()
        await session_repo.set_title(session_id, title)
        await db.commit()

    # 4. Load conversation history for agent context
    history = await msg_repo.list_by_session(session_id)

    # 5. Stream
    async def event_generator() -> AsyncGenerator[str, None]:
        orchestrator = AgentOrchestrator()
        start_time = time.monotonic()
        full_content = ""
        sources = []
        artifact_id = None

        try:
            async for event in orchestrator.run_stream(
                session_id=session_id,
                user_message=body.content,
                history=history,
                db=db,
            ):
                event_type = event.get("type")

                if event_type == "token":
                    delta = event["delta"]
                    full_content += delta
                    yield _sse(SSETokenEvent(delta=delta))

                elif event_type == "sources":
                    sources = event["sources"]

                elif event_type == "artifact_id":
                    artifact_id = event["artifact_id"]

                elif event_type == "done":
                    # Persist assistant message with metadata
                    latency_ms = int((time.monotonic() - start_time) * 1000)
                    assistant_msg = await msg_repo.create(
                        session_id=session_id,
                        role="assistant",
                        content=full_content,
                        sources=sources,
                        latency_ms=latency_ms,
                    )
                    await db.commit()

                    yield _sse(
                        SSEDoneEvent(
                            message_id=assistant_msg.id,
                            sources=sources or None,
                            artifact_id=artifact_id,
                        )
                    )

        except Exception as exc:
            logger.exception("stream_error", session_id=str(session_id), error=str(exc))
            yield _sse(
                SSEErrorEvent(
                    code=getattr(exc, "error_code", "INTERNAL_ERROR"),
                    message=str(exc),
                )
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
