"""
recruit_engine — the Recruit-ME core engine.

Pure library. It scrapes job sources, scores postings against a parsed résumé,
and builds a report. It never touches a database, reads no environment for
configuration, performs no auth, and owns no scheduling. Everything the engine
needs is passed in as an ``EngineInput`` plus a set of injected ports
(:mod:`recruit_engine.ports`); everything it produces comes back as an
``EngineResult``.

The same engine build runs for every tenant — all per-user variation is data.
"""

from .types import (
    EngineInput,
    EngineLimits,
    EngineResult,
    JobPosting,
    MatchedJob,
    ProfileSpec,
    ResumeParse,
    SourceCredential,
)

__version__ = "0.1.0"

__all__ = [
    "EngineInput",
    "EngineLimits",
    "EngineResult",
    "JobPosting",
    "MatchedJob",
    "ProfileSpec",
    "ResumeParse",
    "SourceCredential",
]
