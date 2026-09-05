"""CRUD for a tenant's job profiles. Every query is scoped by user_id."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import NotFoundError
from ..models.job_profile import JobProfile
from ..schemas.job_profile import JobProfileIn, JobProfilePatch


class JobProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: uuid.UUID, data: JobProfileIn) -> JobProfile:
        profile = JobProfile(user_id=user_id, **data.model_dump())
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def list(self, user_id: uuid.UUID) -> list[JobProfile]:
        rows = await self.db.scalars(
            select(JobProfile)
            .where(JobProfile.user_id == user_id)
            .order_by(JobProfile.created_at.desc())
        )
        return list(rows)

    async def get(self, user_id: uuid.UUID, profile_id: uuid.UUID) -> JobProfile:
        profile = await self.db.get(JobProfile, profile_id)
        if profile is None or profile.user_id != user_id:
            raise NotFoundError("job profile not found")
        return profile

    async def update(
        self, user_id: uuid.UUID, profile_id: uuid.UUID, patch: JobProfilePatch
    ) -> JobProfile:
        profile = await self.get(user_id, profile_id)
        for field, value in patch.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def delete(self, user_id: uuid.UUID, profile_id: uuid.UUID) -> None:
        profile = await self.get(user_id, profile_id)
        await self.db.delete(profile)
        await self.db.flush()

    async def set_active(
        self, user_id: uuid.UUID, profile_id: uuid.UUID, active: bool
    ) -> JobProfile:
        profile = await self.get(user_id, profile_id)
        profile.is_active = active
        await self.db.flush()
        await self.db.refresh(profile)
        return profile
