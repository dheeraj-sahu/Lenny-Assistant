"""
schemas/artifact_schemas.py

Pydantic v2 request/response schemas for artifact endpoints.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ArtifactResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    message_id: uuid.UUID | None
    artifact_type: Literal["markdown", "html"]
    title: str | None
    sanitized_content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ArtifactListResponse(BaseModel):
    artifacts: list[ArtifactResponse]
