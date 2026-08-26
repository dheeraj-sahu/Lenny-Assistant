"""
persistence/repositories/artifact_repository.py

CRUD operations for the `artifacts` table.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.models import Artifact


class ArtifactRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        session_id: uuid.UUID,
        artifact_type: str,
        raw_content: str,
        sanitized_content: str,
        title: str | None = None,
        message_id: uuid.UUID | None = None,
    ) -> Artifact:
        """Persist a new artifact and return the saved object."""
        artifact = Artifact(
            session_id=session_id,
            message_id=message_id,
            artifact_type=artifact_type,
            title=title,
            raw_content=raw_content,
            sanitized_content=sanitized_content,
        )
        self.db.add(artifact)
        await self.db.flush()
        await self.db.refresh(artifact)
        return artifact

    async def get_by_id(self, artifact_id: uuid.UUID) -> Artifact | None:
        result = await self.db.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: uuid.UUID) -> list[Artifact]:
        """Return all artifacts for a session, newest first."""
        result = await self.db.execute(
            select(Artifact)
            .where(Artifact.session_id == session_id)
            .order_by(Artifact.created_at.desc())
        )
        return list(result.scalars().all())
