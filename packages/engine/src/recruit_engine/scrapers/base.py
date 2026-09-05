"""
The target shape every scraper converges on in Phase 4.4.

Defined now so the contract is visible and reviewable. The concrete scrapers in
this package still expose their original free functions (see ``__init__.py``);
they are adapted to this protocol in Phase 4.4, not before.
"""

from __future__ import annotations

from typing import Protocol

from ..ports import RateLimiter
from ..types import JobPosting, ProfileSpec, SourceCredential


class Scraper(Protocol):
    site: str

    async def fetch(
        self,
        spec: ProfileSpec,
        cred: SourceCredential | None,
        rl: RateLimiter,
        *,
        timeout_s: int,
    ) -> list[JobPosting]: ...
