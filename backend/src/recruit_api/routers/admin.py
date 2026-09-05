"""/api/v1/admin — RBAC-gated scaffolding for future admin/paid tiers."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..errors import NotFoundError
from ..models.user import User, UserStatus
from ..schemas.common import Page
from ..schemas.user import UserOut
from ..security.deps import require_role

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role("admin"))],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/users", response_model=Page[UserOut])
async def list_users(
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[UserOut]:
    total = await db.scalar(select(func.count()).select_from(User)) or 0
    rows = await db.scalars(
        select(User)
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page[UserOut](
        items=[UserOut.model_validate(u) for u in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/users/{user_id}:suspend", response_model=UserOut)
async def suspend_user(user_id: uuid.UUID, db: DbDep) -> UserOut:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("user not found")
    user.status = UserStatus.suspended
    await db.flush()
    return UserOut.model_validate(user)
