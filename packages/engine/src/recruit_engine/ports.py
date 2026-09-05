"""
Ports — the capabilities the engine depends on but never implements.

The worker supplies concrete adapters (Postgres-backed seen-store, Redis token
bucket, OpenRouter client, wall clock). Tests supply fakes. The engine only ever
sees these Protocols, which is what keeps one engine build tenant-agnostic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class SeenStore(Protocol):
    """Deduplication across runs, scoped per tenant."""

    def filter_new(self, tenant_id: str, hashes: list[str]) -> set[str]:
        """Return the subset of ``hashes`` this tenant has not seen before."""
        ...

    def mark_seen(self, tenant_id: str, hashes: list[str]) -> None: ...


@runtime_checkable
class RateLimiter(Protocol):
    """A token bucket. ``key`` is typically ``f"{site}:{tenant_id}"``."""

    async def acquire(self, key: str) -> None:
        """Block until a token is available for ``key``."""
        ...


@runtime_checkable
class LLMClient(Protocol):
    async def complete(self, prompt: str, *, temperature: float = 0.0) -> str: ...


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...
