"""A small fail-open rate limiter for the unauthenticated auth routes.

Fixed-window counters in Redis, keyed by ``bucket:client-ip``. If Redis is
unreachable the request is allowed (an auth outage must not lock everyone out).
Disabled when ``env == "test"`` so the suite isn't rate-limited.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request

from ..config import get_settings
from ..errors import AppError

logger = logging.getLogger("recruit_api.ratelimit")

_redis = None


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"


async def _get_redis():
    global _redis
    if _redis is None:
        from redis.asyncio import Redis

        _redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(
    bucket: str, *, limit: int, window_s: int
) -> Callable[[Request], Coroutine[Any, Any, None]]:
    async def _dep(request: Request) -> None:
        if get_settings().env == "test":
            return
        key = f"rl:auth:{bucket}:{_client_ip(request)}"
        try:
            redis = await _get_redis()
            n = await redis.incr(key)
            if n == 1:
                await redis.expire(key, window_s)
        except Exception:  # noqa: BLE001 — fail open
            logger.warning("rate-limit check skipped (redis unavailable)")
            return
        if n > limit:
            raise RateLimitedError("too many requests — try again shortly")

    return _dep
