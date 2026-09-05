"""User account model."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_pk


class UserRole(enum.StrEnum):
    user = "user"
    admin = "admin"


class UserPlan(enum.StrEnum):
    free = "free"
    pro = "pro"


class UserStatus(enum.StrEnum):
    pending_verification = "pending_verification"
    active = "active"
    suspended = "suspended"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(CITEXT, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20), default=UserRole.user, nullable=False
    )
    plan: Mapped[UserPlan] = mapped_column(
        Enum(UserPlan, native_enum=False, length=20), default=UserPlan.free, nullable=False
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, native_enum=False, length=30),
        default=UserStatus.pending_verification,
        nullable=False,
    )
