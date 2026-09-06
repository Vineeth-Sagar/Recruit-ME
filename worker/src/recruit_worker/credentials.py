"""Open sealed site credentials — worker-only.

Nothing in ``recruit_api.routers`` imports this module. Decryption lives here
and in :mod:`recruit_worker.tasks.verify_credential` so the web process never
holds a plaintext secret.
"""

from __future__ import annotations

import json
import logging
import uuid

from recruit_api.models.site_credential import CredentialStatus, SiteCredential
from recruit_api.security.crypto import CryptoError, Envelope
from recruit_engine.types import SourceCredential
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("recruit_worker.credentials")


def open_secret(envelope: Envelope, row: SiteCredential) -> dict:
    """Decrypt one row's secret map. Raises :class:`CryptoError` on failure."""
    raw = envelope.decrypt(row.secret_ciphertext, row.nonce, row.key_version)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise CryptoError("decrypted secret is not an object")
    return data


async def load_source_credentials(
    db: AsyncSession, user_id: uuid.UUID, envelope: Envelope
) -> list[SourceCredential]:
    """Every usable credential for a tenant, decrypted into engine form.

    Rows known to be bad (``status == invalid``) are skipped so a run does not
    waste a scrape on them; unverified rows are still tried.
    """
    rows = await db.scalars(select(SiteCredential).where(SiteCredential.user_id == user_id))
    out: list[SourceCredential] = []
    for row in rows:
        if row.status == CredentialStatus.invalid:
            continue
        try:
            secret = open_secret(envelope, row)
        except (CryptoError, ValueError):
            logger.error(
                "credential %s (user %s, %s) failed to decrypt — skipping",
                row.id,
                user_id,
                row.site,
            )
            continue
        out.append(
            SourceCredential(site=str(row.site), auth_type=str(row.auth_type), secret=secret)
        )
    return out
