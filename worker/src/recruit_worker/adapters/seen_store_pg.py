"""``SeenStore`` port over the ``job_matches`` table.

A hash is "seen" once a ``job_matches`` row exists for ``(user_id, hash)``. The
worker preloads the user's known hashes (just the one column) before calling
``run_engine`` so ``filter_new`` stays synchronous, as the port requires.

``mark_seen`` is a no-op — the authoritative write is ``persistence.save_result``
inserting the match rows ``ON CONFLICT DO NOTHING``, so a retried run re-checks
``filter_new`` and skips anything already persisted.
"""

from __future__ import annotations

import uuid

from recruit_api.models.run import JobMatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def load_known_hashes(db: AsyncSession, user_id: uuid.UUID) -> set[str]:
    rows = await db.scalars(select(JobMatch.external_hash).where(JobMatch.user_id == user_id))
    return set(rows)


class PgSeenStore:
    def __init__(self, known: set[str]):
        self._known = known

    def filter_new(self, tenant_id: str, hashes: list[str]) -> set[str]:
        return {h for h in hashes if h not in self._known}

    def mark_seen(self, tenant_id: str, hashes: list[str]) -> None:
        self._known.update(hashes)
