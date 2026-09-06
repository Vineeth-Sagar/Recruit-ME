"""/api/v1/matches — dashboard data: filter, inspect, mark saved/applied/dismissed."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..errors import NotFoundError
from ..models.run import JobMatch, MatchStatus
from ..schemas.common import Page
from ..schemas.run import MatchOut, MatchPatchIn
from ..security.deps import CurrentUser

router = APIRouter(prefix="/matches", tags=["matches"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=Page[MatchOut])
async def list_matches(
    user: CurrentUser,
    db: DbDep,
    run: uuid.UUID | None = None,
    profile: uuid.UUID | None = None,
    match_status: Annotated[MatchStatus | None, Query(alias="status")] = None,
    min_match: Annotated[int, Query(ge=0, le=100)] = 0,
    q: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Page[MatchOut]:
    where = [JobMatch.user_id == user.id, JobMatch.match_percentage >= min_match]
    if run is not None:
        where.append(JobMatch.run_id == run)
    if profile is not None:
        where.append(JobMatch.job_profile_id == profile)
    if match_status is not None:
        where.append(JobMatch.status == match_status)
    if q:
        like = f"%{q}%"
        where.append(or_(JobMatch.company.ilike(like), JobMatch.title.ilike(like)))

    total = await db.scalar(select(func.count()).select_from(JobMatch).where(*where)) or 0
    rows = await db.scalars(
        select(JobMatch)
        .where(*where)
        .order_by(JobMatch.match_percentage.desc(), JobMatch.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page[MatchOut](
        items=[MatchOut.model_validate(m) for m in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{match_id}", response_model=MatchOut)
async def patch_match(
    match_id: uuid.UUID, body: MatchPatchIn, user: CurrentUser, db: DbDep
) -> MatchOut:
    m = await db.get(JobMatch, match_id)
    if m is None or m.user_id != user.id:
        raise NotFoundError("match not found")
    m.status = body.status
    m.applied_at = datetime.now(UTC) if body.status == MatchStatus.applied else m.applied_at
    await db.flush()
    await db.refresh(m)
    return MatchOut.model_validate(m)
