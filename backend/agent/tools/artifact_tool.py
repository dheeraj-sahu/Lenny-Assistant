"""
agent/tools/artifact_tool.py

Tool definition and handler for generate_artifact.
Classifies, sanitizes, and persists content; returns the artifact ID.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from artifacts.artifact_service import create_artifact
from core.logging import get_logger

logger = get_logger(__name__)

# ── Anthropic tool definition ─────────────────────────────────────────────────

GENERATE_ARTIFACT_TOOL_DEFINITION = {
    "name": "generate_artifact",
    "description": (
        "Package content as a standalone Markdown or HTML artifact for the in-app viewer. "
        "Use this after generating essays, one-pagers, or HTML documents. "
        "Only invoke when the user explicitly requests an artifact or document viewer."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The full Markdown or HTML content of the artifact.",
            },
            "artifact_type": {
                "type": "string",
                "enum": ["markdown", "html"],
                "description": "Content type. Use 'markdown' for text/essays, 'html' for rich layouts.",
            },
            "title": {
                "type": "string",
                "description": "Optional short title for the artifact (displayed in the viewer header).",
            },
        },
        "required": ["content", "artifact_type"],
    },
}


# ── Async tool handler ────────────────────────────────────────────────────────

async def handle_generate_artifact(
    content: str,
    artifact_type: str,
    session_id: uuid.UUID,
    db: AsyncSession,
    title: str | None = None,
    message_id: uuid.UUID | None = None,
) -> dict:
    """
    Sanitize and persist an artifact.

    Returns:
        {"artifact_id": str, "artifact_type": str, "sanitized_len": int}
    """
    artifact = await create_artifact(
        db=db,
        session_id=session_id,
        content=content,
        artifact_type=artifact_type,  # type: ignore[arg-type]
        title=title,
        message_id=message_id,
    )
    await db.commit()

    return {
        "artifact_id": str(artifact.id),
        "artifact_type": artifact.artifact_type,
        "sanitized_len": len(artifact.sanitized_content),
    }
