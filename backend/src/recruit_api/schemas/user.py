from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.user import UserPlan, UserRole, UserStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    plan: UserPlan
    status: UserStatus
    created_at: datetime


class UserUpdateIn(BaseModel):
    full_name: str | None = None
