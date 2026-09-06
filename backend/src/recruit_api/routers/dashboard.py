"""/api/v1/dashboard — aggregate data for the home screen."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..security.deps import CurrentUser
from ..services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/summary")
async def dashboard_summary(user: CurrentUser, db: DbDep) -> dict:
    return await DashboardService(db).summary(user.id)
