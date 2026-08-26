"""
artifacts/artifact_service.py

Persist and retrieve artifacts.
Handles: classify type → sanitize → store raw + sanitized → return artifact record.
"""

import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from artifacts.sanitizer import sanitize_content
from core.logging import get_logger
from persistence.models import Artifact
from persistence.repositories.artifact_repository import ArtifactRepository

logger = get_logger(__name__)


def classify_artifact_type(content: str) -> Literal["markdown", "html"]:
    """
    Classify content as 'html' if it contains HTML tags, else 'markdown'.
    Simple heuristic sufficient for this use case.
    """
    stripped = content.strip()
    if stripped.startswith("<!DOCTYPE") or stripped.startswith("<html"):
        return "html"
    # Check for any meaningful HTML tags
    import re
    if re.search(r"<(div|span|p|table|ul|ol|h[1-6]|a\s|img\s)[^>]*>", content, re.IGNORECASE):
        return "html"
    return "markdown"


async def create_artifact(
    db: AsyncSession,
    session_id: uuid.UUID,
    content: str,
    artifact_type: Literal["markdown", "html"] | None = None,
    title: str | None = None,
    message_id: uuid.UUID | None = None,
) -> Artifact:
    """
    Sanitize and persist an artifact.

    1. Classify type if not provided.
    2. Sanitize (HTML goes through nh3; Markdown is returned as-is).
    3. Store both raw and sanitized versions.
    4. Return the saved Artifact ORM object.
    """
    if artifact_type is None:
        artifact_type = classify_artifact_type(content)

    sanitized = sanitize_content(content, artifact_type)

    repo = ArtifactRepository(db)
    artifact = await repo.create(
        session_id=session_id,
        artifact_type=artifact_type,
        raw_content=content,
        sanitized_content=sanitized,
        title=title,
        message_id=message_id,
    )

    logger.info(
        "artifact_created",
        artifact_id=str(artifact.id),
        type=artifact_type,
        raw_len=len(content),
        sanitized_len=len(sanitized),
    )
    return artifact
