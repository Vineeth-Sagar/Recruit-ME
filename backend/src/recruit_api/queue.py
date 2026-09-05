"""Enqueue side of the job queue (arq/Redis).

The API only ever *enqueues*; the worker (``recruit_worker``) consumes. Tests
override the ``get_enqueue`` dependency with a recorder.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from .config import get_settings

Enqueue = Callable[..., Awaitable[None]]

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
    await pool.enqueue_job(fn, *args)


def get_enqueue() -> Enqueue:
    return enqueue
