"""Runs: create (→ enqueue), list, detail, cancel, live event stream.

Automation never runs here — ``create`` writes a queued ``Run`` row, enqueues
``execute_run``, and returns ``202``.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ConflictError, NotFoundError
from ..models.job_profile import JobProfile
from ..models.run import (
    TERMINAL_RUN_STATUSES,
    Run,
    RunSource,
    RunStatus,
    RunStep,
    RunTrigger,
)
from ..queue import Enqueue


def _now() -> datetime:
    return datetime.now(UTC)


class RunService:
    def __init__(self, db: AsyncSession, enqueue: Enqueue):
        self.db = db
        self.enqueue = enqueue

    async def _owned_profile(self, user_id: uuid.UUID, profile_id: uuid.UUID) -> JobProfile:
        profile = await self.db.get(JobProfile, profile_id)
        if profile is None or profile.user_id != user_id:
            raise NotFoundError("job profile not found")
        return profile

    async def create(
        self,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        *,
        trigger: RunTrigger = RunTrigger.manual,
        idempotency_key: str | None = None,
    ) -> tuple[Run, bool]:
        await self._owned_profile(user_id, profile_id)
        key = idempotency_key or f"{trigger.value}:{profile_id}:{uuid.uuid4().hex}"

        existing = await self.db.scalar(select(Run).where(Run.idempotency_key == key))
        if existing is not None:
            if existing.user_id != user_id:
                raise ConflictError("idempotency key already used")
            return existing, False

        run = Run(
            user_id=user_id,
            job_profile_id=profile_id,
            trigger=trigger,
            status=RunStatus.queued,
            idempotency_key=key,
            queued_at=_now(),
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)
        # Commit before enqueue so the worker's own session can see the row.
        await self.db.commit()
        await self.enqueue("execute_run", str(run.id))
        return run, True

    async def get(self, user_id: uuid.UUID, run_id: uuid.UUID) -> Run:
        run = await self.db.get(Run, run_id)
        if run is None or run.user_id != user_id:
            raise NotFoundError("run not found")
        return run

    async def steps(self, run_id: uuid.UUID) -> list[RunStep]:
        return list(
            await self.db.scalars(
                select(RunStep).where(RunStep.run_id == run_id).order_by(RunStep.at)
            )
        )

    async def sources(self, run_id: uuid.UUID) -> list[RunSource]:
        return list(
            await self.db.scalars(
                select(RunSource).where(RunSource.run_id == run_id).order_by(RunSource.source)
            )
        )

    async def list(
        self,
        user_id: uuid.UUID,
        *,
        status: RunStatus | None = None,
        profile_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Run], int]:
        where = [Run.user_id == user_id]
        if status is not None:
            where.append(Run.status == status)
        if profile_id is not None:
            where.append(Run.job_profile_id == profile_id)

        total = await self.db.scalar(select(func.count()).select_from(Run).where(*where)) or 0
        rows = await self.db.scalars(
            select(Run)
            .where(*where)
            .order_by(Run.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), total

    async def cancel(self, user_id: uuid.UUID, run_id: uuid.UUID) -> Run:
        run = await self.get(user_id, run_id)
        if run.status not in TERMINAL_RUN_STATUSES:
            run.status = RunStatus.cancelled
            run.finished_at = _now()
            await self.db.flush()
            await self.db.refresh(run)
        return run

    async def stream_events(
        self, user_id: uuid.UUID, run_id: uuid.UUID, *, poll_s: float = 1.0, max_polls: int = 900
    ) -> AsyncIterator[str]:
        run = await self.get(user_id, run_id)
        sent = 0
        for _ in range(max_polls):
            for step in (await self.steps(run_id))[sent:]:
                sent += 1
                yield _sse(
                    "step",
                    {
                        "name": step.name,
                        "status": step.status,
                        "detail": step.detail,
                        "at": step.at.isoformat(),
                    },
                )
            await self.db.refresh(run)
            if run.status in TERMINAL_RUN_STATUSES:
                yield _sse("done", {"status": str(run.status), "stats": run.stats})
                return
            await asyncio.sleep(poll_s)
        yield _sse("timeout", {"status": str(run.status)})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
