"""
The engine's typed contract.

``EngineInput`` is everything a run needs, assembled by the caller (the worker)
from that tenant's database rows. ``EngineResult`` is everything a run produces,
for the caller to persist. Nothing here imports a driver, a client, or a
setting — these are plain data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ─────────────────────────────────────────────────────────────────
# Input
# ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProfileSpec:
    """A tenant's job profile, flattened to exactly what the engine reads."""

    profile_id: str
    target_roles: list[str]
    locations: list[str]
    job_types: list[str] = field(default_factory=list)
    min_match_percent: int = 50
    must_have_skills: list[str] = field(default_factory=list)
    nice_to_have_skills: list[str] = field(default_factory=list)
    exclude_companies: list[str] = field(default_factory=list)
    watchlist_companies: list[str] = field(default_factory=list)
    # Gates LinkedIn / Indeed / Glassdoor (via python-jobspy). Off by default;
    # a run only touches the big-3 when the tenant has opted in with consent.
    big3_optin: bool = False


@dataclass(frozen=True)
class ResumeParse:
    """A parsed résumé. ``parsed`` is the structured JSON the LLM returned."""

    resume_id: str
    parsed: dict
    skills: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SourceCredential:
    """A decrypted credential for one job site. In-memory only, never logged."""

    site: str
    auth_type: str  # "cookie" | "api_key" | "none"
    secret: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EngineLimits:
    per_source_timeout_s: int = 300
    match_batch_size: int = 20
    llm_max_concurrency: int = 1


@dataclass(frozen=True)
class EngineInput:
    run_id: str
    tenant_id: str
    profile: ProfileSpec
    resumes: list[ResumeParse]
    enabled_sources: list[str]
    credentials: list[SourceCredential] = field(default_factory=list)
    limits: EngineLimits = field(default_factory=EngineLimits)


# ─────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────


@dataclass
class JobPosting:
    source: str
    company: str
    title: str
    location: str = ""
    description: str = ""
    url: str = ""
    posted_date: str | None = None
    salary: str | None = None
    external_hash: str = ""


@dataclass
class MatchedJob:
    job: JobPosting
    match_percentage: int
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    why_fit: str = ""
    urgency: str = "LOW"
    recommended_action: str = "Optional"
    matched_profile_id: str = ""


@dataclass
class EngineResult:
    run_id: str
    scraped: int = 0
    new: int = 0
    matched: list[MatchedJob] = field(default_factory=list)
    # {source: {"status": str, "found": int, "latency_ms": int, "error": str | None}}
    per_source: dict[str, dict] = field(default_factory=dict)
    missing_skills_tally: dict[str, int] = field(default_factory=dict)
    report_bytes: bytes | None = None
    ai_degraded: bool = False
