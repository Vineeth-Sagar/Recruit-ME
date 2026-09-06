"""Per-site politeness policy for the rate limiter.

``rpm`` / ``burst`` bound one tenant against a site; ``global_rpm`` /
``global_burst`` cap all tenants combined so one user's run can't get the
shared egress IP blocked for everyone.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SitePolicy:
    rpm: int = 20
    burst: int = 5
    global_rpm: int = 120
    global_burst: int = 20
    min_delay_ms: int = 0


DEFAULT_POLICY = SitePolicy()

SITE_POLICIES: dict[str, SitePolicy] = {
    # jobspy fans out to LinkedIn/Indeed/Glassdoor — keep it gentle.
    "jobspy": SitePolicy(rpm=6, burst=2, global_rpm=20, global_burst=5, min_delay_ms=500),
    "wellfound": SitePolicy(rpm=15, burst=4, global_rpm=60, global_burst=15),
    "yc": SitePolicy(rpm=30, burst=10, global_rpm=120, global_burst=30),
    "hackernews": SitePolicy(rpm=30, burst=10, global_rpm=120, global_burst=30),
    # LLM provider — the free tier is ~10 RPM; treat it like a site.
    "openrouter": SitePolicy(rpm=10, burst=3, global_rpm=15, global_burst=5),
}


def policy_for(site: str) -> SitePolicy:
    return SITE_POLICIES.get(site, DEFAULT_POLICY)
