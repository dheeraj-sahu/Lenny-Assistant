"""
persistence/repositories/session_repository.py

CRUD operations for the `sessions` table.
All methods accept an AsyncSession injected via FastAPI's Depends(get_db).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.models import Session


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, active_provider: str) -> Session:
        """Create a new session and return it."""
        session = Session(active_provider=active_provider)
        self.db.add(session)
        await self.db.flush()  # get the generated id without committing
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        """Return a session by primary key, or None if not found."""
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[Session]:
        """Return sessions ordered by creation time (newest first)."""
        result = await self.db.execute(
            select(Session).order_by(Session.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def set_title(self, session_id: uuid.UUID, title: str) -> None:
        """Set the session title (derived from the first user message)."""
        await self.db.execute(
            update(Session).where(Session.id == session_id).values(title=title)
        )

    async def delete(self, session_id: uuid.UUID) -> bool:
        """Soft-delete is out of scope; hard-delete cascade to messages/artifacts."""
        session = await self.get_by_id(session_id)
        if not session:
            return False
        await self.db.delete(session)
        return True
