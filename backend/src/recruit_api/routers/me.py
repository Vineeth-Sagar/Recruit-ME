"""/api/v1/me — the caller's own account."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..schemas.user import UserOut, UserUpdateIn
from ..security.deps import CurrentUser

router = APIRouter(prefix="/me", tags=["me"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=UserOut)
async def read_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("", response_model=UserOut)
async def update_me(body: UserUpdateIn, user: CurrentUser, db: DbDep) -> UserOut:
    if body.full_name is not None:
        user.full_name = body.full_name
    await db.flush()
    return UserOut.model_validate(user)
