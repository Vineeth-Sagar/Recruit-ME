from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    job_types: list[str] = Field(default_factory=list)
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    exclude_companies: list[str] = Field(default_factory=list)
    watchlist_companies: list[str] = Field(default_factory=list)
    min_match_percent: int = Field(default=50, ge=0, le=100)
    min_salary: int = Field(default=0, ge=0)
    schedule_cron: str | None = Field(default=None, max_length=120)
    timezone: str = Field(default="Asia/Kolkata", max_length=64)


class JobProfilePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_roles: list[str] | None = None
    locations: list[str] | None = None
    job_types: list[str] | None = None
    must_have_skills: list[str] | None = None
    nice_to_have_skills: list[str] | None = None
    exclude_companies: list[str] | None = None
    watchlist_companies: list[str] | None = None
    min_match_percent: int | None = Field(default=None, ge=0, le=100)
    min_salary: int | None = Field(default=None, ge=0)
    schedule_cron: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)


class JobProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    is_active: bool
    target_roles: list[str]
    locations: list[str]
    job_types: list[str]
    must_have_skills: list[str]
    nice_to_have_skills: list[str]
    exclude_companies: list[str]
    watchlist_companies: list[str]
    min_match_percent: int
    min_salary: int
    big3_optin: bool
    schedule_cron: str | None
    timezone: str
    created_at: datetime
    updated_at: datetime
