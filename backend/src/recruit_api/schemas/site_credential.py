from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.site_credential import CredentialAuthType, CredentialSite, CredentialStatus

# A generous ceiling on the serialised secret so a stray paste can't bloat a row.
_MAX_SECRET_BYTES = 16 * 1024


class SiteCredentialIn(BaseModel):
    """The write payload. ``secret`` is a small map — e.g. ``{"li_at": "..."}``
    for a LinkedIn session cookie, ``{"api_key": "..."}`` for a key. It is sealed
    immediately and never stored or echoed in plaintext."""

    auth_type: CredentialAuthType = CredentialAuthType.cookie
    secret: dict[str, str] = Field(min_length=1)
    label: str = Field(default="", max_length=120)

    @field_validator("secret")
    @classmethod
    def _reject_empty_and_oversize(cls, v: dict[str, str]) -> dict[str, str]:
        if not any(val.strip() for val in v.values()):
            raise ValueError("secret has no non-empty values")
        size = sum(len(k) + len(val) for k, val in v.items())
        if size > _MAX_SECRET_BYTES:
            raise ValueError("secret payload is too large")
        return v


class SiteCredentialOut(BaseModel):
    """Everything about a stored credential *except* the secret."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site: CredentialSite
    auth_type: CredentialAuthType
    status: CredentialStatus
    label: str
    last_verified_at: datetime | None
    verify_error: str
    created_at: datetime
    updated_at: datetime
