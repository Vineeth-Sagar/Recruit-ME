"""A tenant's credential for one job site — sealed at rest.

The plaintext secret is never stored. Each row keeps the ChaCha20-Poly1305
``secret_ciphertext``, its ``nonce``, and the ``key_version`` of the master key
used to seal it (see :mod:`recruit_api.security.crypto`).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_pk


class CredentialSite(enum.StrEnum):
    linkedin = "linkedin"
    indeed = "indeed"
    glassdoor = "glassdoor"
    wellfound = "wellfound"


class CredentialAuthType(enum.StrEnum):
    cookie = "cookie"
    api_key = "api_key"
    session = "session"


class CredentialStatus(enum.StrEnum):
    unverified = "unverified"
    valid = "valid"
    invalid = "invalid"
    expired = "expired"


class SiteCredential(Base, TimestampMixin):
    __tablename__ = "site_credentials"
    __table_args__ = (UniqueConstraint("user_id", "site", name="uq_site_credentials_user_site"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    site: Mapped[CredentialSite] = mapped_column(
        Enum(CredentialSite, native_enum=False, length=20), nullable=False
    )
    auth_type: Mapped[CredentialAuthType] = mapped_column(
        Enum(CredentialAuthType, native_enum=False, length=20),
        default=CredentialAuthType.cookie,
        nullable=False,
    )

    secret_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False)

    label: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    status: Mapped[CredentialStatus] = mapped_column(
        Enum(CredentialStatus, native_enum=False, length=20),
        default=CredentialStatus.unverified,
        nullable=False,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verify_error: Mapped[str] = mapped_column(String(400), default="", nullable=False)
