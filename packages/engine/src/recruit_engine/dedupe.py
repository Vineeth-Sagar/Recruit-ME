"""
Job identity.

``compute_external_hash`` is a stable fingerprint for a posting. The engine
asks the injected ``SeenStore`` (a Postgres ``job_matches`` table keyed by
``(user_id, external_hash)`` in the worker) which hashes are new; there is no
local database here any more.

The fingerprint is built from the posting URL when there is one — normalised so
tracking params and host casing don't matter — because that is the one field
that is stable run-to-run and distinct between genuinely different openings.
``source`` is deliberately excluded: jobspy reports it inconsistently
(``"LinkedIn"`` vs ``"linkedin,indeed"`` vs a fallback string), which would make
the same posting hash three different ways. Without a URL we fall back to
company + title + location.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlsplit

from .types import JobPosting


def _norm_url(raw: str) -> str:
    """Scheme/host-case/``www.``/query/fragment/trailing-slash insensitive."""
    try:
        parts = urlsplit(raw.strip())
    except ValueError:
        return raw.strip().lower()
    if not parts.netloc:
        return raw.strip().lower()
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/")
    return f"{host}{path}"


def compute_external_hash(job: JobPosting) -> str:
    """Stable fingerprint for a posting. URL-based when available."""
    url = _norm_url(job.url or "")
    if url:
        key = f"url:{url}"
    else:
        key = "meta:" + "|".join(
            part.lower().strip() for part in (job.company, job.title, job.location)
        )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()
