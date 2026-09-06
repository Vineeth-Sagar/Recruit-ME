"""Per-tenant job-site credentials.

The API layer only ever *seals* a secret (:meth:`SiteCredentialService.upsert`)
and never opens one. Decryption for a run happens exclusively in the worker
(``recruit_worker.credentials`` / ``recruit_worker.tasks.verify_credential``),
so a compromised web process cannot read stored secrets.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import NotFoundError
from ..models.site_credential import CredentialSite, CredentialStatus, SiteCredential
from ..queue import Enqueue
from ..schemas.site_credential import SiteCredentialIn
from ..security.crypto import Envelope


class SiteCredentialService:
    def __init__(self, db: AsyncSession, envelope: Envelope, enqueue: Enqueue):
        self.db = db
        self.envelope = envelope
        self.enqueue = enqueue

    async def list(self, user_id: uuid.UUID) -> list[SiteCredential]:
        rows = await self.db.scalars(
            select(SiteCredential)
            .where(SiteCredential.user_id == user_id)
            .order_by(SiteCredential.site)
        )
        return list(rows)

    async def get(self, user_id: uuid.UUID, site: CredentialSite) -> SiteCredential:
        row = await self.db.scalar(
            select(SiteCredential).where(
                SiteCredential.user_id == user_id, SiteCredential.site == site
            )
        )
        if row is None:
            raise NotFoundError("no credential stored for that site")
        return row

    async def upsert(
        self, user_id: uuid.UUID, site: CredentialSite, data: SiteCredentialIn
    ) -> SiteCredential:
        plaintext = json.dumps(data.secret, separators=(",", ":")).encode()
        ciphertext, nonce, key_version = self.envelope.encrypt(plaintext)

        row = await self.db.scalar(
            select(SiteCredential).where(
                SiteCredential.user_id == user_id, SiteCredential.site == site
            )
        )
        if row is None:
            row = SiteCredential(user_id=user_id, site=site)
            self.db.add(row)

        row.auth_type = data.auth_type
        row.label = data.label
        row.secret_ciphertext = ciphertext
        row.nonce = nonce
        row.key_version = key_version
        row.status = CredentialStatus.unverified
        row.verify_error = ""
        row.last_verified_at = None

        await self.db.flush()
        await self.db.refresh(row)
        # Commit before enqueue so the worker's own session sees the fresh row.
        await self.db.commit()
        await self.enqueue("verify_credential", str(row.id))
        return row

    async def verify(self, user_id: uuid.UUID, site: CredentialSite) -> SiteCredential:
        row = await self.get(user_id, site)
        await self.enqueue("verify_credential", str(row.id))
        return row

    async def delete(self, user_id: uuid.UUID, site: CredentialSite) -> None:
        row = await self.get(user_id, site)
        await self.db.delete(row)
        await self.db.flush()
