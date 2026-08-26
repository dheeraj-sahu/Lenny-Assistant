"""
api/routes_artifacts.py

Artifact read endpoints:
  GET /artifacts/{id}                        — fetch one artifact
  GET /sessions/{session_id}/artifacts       — list artifacts for a session
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import ArtifactNotFoundError, SessionNotFoundError
from persistence.database import get_db
from persistence.repositories.artifact_repository import ArtifactRepository
from persistence.repositories.session_repository import SessionRepository
from schemas.artifact_schemas import ArtifactListResponse, ArtifactResponse

router = APIRouter(tags=["Artifacts"])


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """Fetch a single artifact by ID. Returns only sanitized_content."""
    repo = ArtifactRepository(db)
    artifact = await repo.get_by_id(artifact_id)
    if not artifact:
        raise ArtifactNotFoundError(f"Artifact {artifact_id} not found")
    return ArtifactResponse.model_validate(artifact)


@router.get("/sessions/{session_id}/artifacts", response_model=ArtifactListResponse)
async def list_session_artifacts(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ArtifactListResponse:
    """List all artifacts associated with a session."""
    session_repo = SessionRepository(db)
    if not await session_repo.get_by_id(session_id):
        raise SessionNotFoundError(f"Session {session_id} not found")

    artifact_repo = ArtifactRepository(db)
    artifacts = await artifact_repo.list_by_session(session_id)
    return ArtifactListResponse(
        artifacts=[ArtifactResponse.model_validate(a) for a in artifacts]
    )
