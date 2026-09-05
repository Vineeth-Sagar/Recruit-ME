"""/api/v1/job-profiles — CRUD for a tenant's job profiles."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from ..schemas.job_profile import JobProfileIn, JobProfileOut, JobProfilePatch
from ..security.deps import CurrentUser, get_job_profile_service
from ..services.job_profile_service import JobProfileService

router = APIRouter(prefix="/job-profiles", tags=["job-profiles"])

SvcDep = Annotated[JobProfileService, Depends(get_job_profile_service)]


@router.get("", response_model=list[JobProfileOut])
async def list_profiles(user: CurrentUser, svc: SvcDep) -> list[JobProfileOut]:
    return [JobProfileOut.model_validate(p) for p in await svc.list(user.id)]


@router.post("", response_model=JobProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(body: JobProfileIn, user: CurrentUser, svc: SvcDep) -> JobProfileOut:
    return JobProfileOut.model_validate(await svc.create(user.id, body))


@router.get("/{profile_id}", response_model=JobProfileOut)
async def get_profile(profile_id: uuid.UUID, user: CurrentUser, svc: SvcDep) -> JobProfileOut:
    return JobProfileOut.model_validate(await svc.get(user.id, profile_id))


@router.patch("/{profile_id}", response_model=JobProfileOut)
async def update_profile(
    profile_id: uuid.UUID, body: JobProfilePatch, user: CurrentUser, svc: SvcDep
) -> JobProfileOut:
    return JobProfileOut.model_validate(await svc.update(user.id, profile_id, body))


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(profile_id: uuid.UUID, user: CurrentUser, svc: SvcDep) -> None:
    await svc.delete(user.id, profile_id)


@router.post("/{profile_id}:activate", response_model=JobProfileOut)
async def activate_profile(profile_id: uuid.UUID, user: CurrentUser, svc: SvcDep) -> JobProfileOut:
    return JobProfileOut.model_validate(await svc.set_active(user.id, profile_id, True))


@router.post("/{profile_id}:deactivate", response_model=JobProfileOut)
async def deactivate_profile(
    profile_id: uuid.UUID, user: CurrentUser, svc: SvcDep
) -> JobProfileOut:
    return JobProfileOut.model_validate(await svc.set_active(user.id, profile_id, False))
