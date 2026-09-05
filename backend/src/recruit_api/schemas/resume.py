from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.resume import ResumeStatus


class ResumeParseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model: str
    skills: list[str]
    parsed_json: dict
    tokens_used: int
    created_at: datetime


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_profile_id: uuid.UUID | None
    original_filename: str
    content_sha256: str
    size_bytes: int
    mime: str
    status: ResumeStatus
    parse_error: str | None
    created_at: datetime
    parse: ResumeParseOut | None = None
