"""
Scraper registry.

``SCRAPERS`` maps a stable source name to an async ``fetch(spec, cred, rl, *,
timeout_s) -> list[JobPosting]`` adapter (:mod:`recruit_engine.scrapers.adapters`).
The engine gates ``jobspy`` on ``spec.big3_optin`` and acquires a rate-limit
token per source before calling.

Dropped for the SaaS: Naukri, Unstop, Internshala, Cutshort. ``serpapi_scraper``
stays in-tree but unregistered (opt-in, user-supplied key).
"""

from .adapters import SCRAPERS

__all__ = ["SCRAPERS"]
