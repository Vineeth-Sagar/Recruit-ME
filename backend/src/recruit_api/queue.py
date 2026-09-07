"""Enqueue side of the job queue (arq/Redis).

The API only ever *enqueues*; the worker (``recruit_worker``) consumes. Tests
override the ``get_enqueue`` dependency with a recorder.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from .config import get_settings

Enqueue = Callable[..., Awaitable[None]]

# Two arq lists. The pool workers consume JOBS_QUEUE; the single scheduler
# consumes CRON_QUEUE (its cron job lands there and nothing else touches it).
# Every explicit enqueue targets JOBS_QUEUE so a scheduler process can never
# claim — and then drop as "function not found" — a job it does not register.
JOBS_QUEUE = "arq:jobs"
CRON_QUEUE = "arq:cron"

_pool = None


async def _get_pool():
    global _pool
    if _pool is None:
        from arq import create_pool
        from arq.connections import RedisSettings

        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool


async def enqueue(fn: str, *args: object) -> None:
    pool = await _get_pool()
    await pool.enqueue_job(fn, *args, _queue_name=JOBS_QUEUE)


def get_enqueue() -> Enqueue:
    return enqueue
