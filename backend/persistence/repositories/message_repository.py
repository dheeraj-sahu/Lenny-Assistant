"""
persistence/repositories/message_repository.py

CRUD operations for the `messages` table.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.models import Message


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        sources: list[dict] | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        latency_ms: int | None = None,
    ) -> Message:
        """Persist a message and return the saved object."""
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            sources=sources,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def list_by_session(
        self, session_id: uuid.UUID, limit: int = 100
    ) -> list[Message]:
        """Return all messages for a session, oldest first."""
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, message_id: uuid.UUID) -> Message | None:
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def update_content(self, message_id: uuid.UUID, content: str) -> None:
        """Update content after streaming completes."""
        from sqlalchemy import update
        await self.db.execute(
            update(Message).where(Message.id == message_id).values(content=content)
        )

    async def update_metadata(
        self,
        message_id: uuid.UUID,
        sources: list[dict] | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        latency_ms: int | None = None,
    ) -> None:
        """Update observability fields after generation completes."""
        from sqlalchemy import update
        values: dict = {}
        if sources is not None:
            values["sources"] = sources
        if prompt_tokens is not None:
            values["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            values["completion_tokens"] = completion_tokens
        if latency_ms is not None:
            values["latency_ms"] = latency_ms
        if values:
            await self.db.execute(
                update(Message).where(Message.id == message_id).values(**values)
            )
