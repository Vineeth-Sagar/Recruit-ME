from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.run import MatchStatus, RunStatus, RunTrigger


class RunCreateIn(BaseModel):
    job_profile_id: uuid.UUID


class RunStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    status: str
    detail: dict
    at: datetime


class RunSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    status: str
    jobs_found: int
    latency_ms: int
    error: str | None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_profile_id: uuid.UUID
    trigger: RunTrigger
    status: RunStatus
    attempt: int
    queued_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    notified_at: datetime | None
    error_summary: str | None
    stats: dict
    created_at: datetime


class RunDetailOut(RunOut):
    steps: list[RunStepOut] = []
    sources: list[RunSourceOut] = []


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID | None
    job_profile_id: uuid.UUID | None
    source: str
    company: str
    title: str
    location: str
    url: str
    salary: str
    posted_date: str
    match_percentage: int
    matched_skills: list[str]
    missing_skills: list[str]
    why_fit: str
    urgency: str
    recommended_action: str
    status: MatchStatus
    applied_at: datetime | None
    created_at: datetime


class MatchPatchIn(BaseModel):
    status: MatchStatus
