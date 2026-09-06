"""
Job identity.

``compute_external_hash`` is a stable fingerprint for a posting. The engine
asks the injected ``SeenStore`` (a Postgres ``job_matches`` table keyed by
``(user_id, external_hash)`` in the worker) which hashes are new; there is no
local database here any more.
"""

from __future__ import annotations

import hashlib

from .types import JobPosting


def compute_external_hash(job: JobPosting) -> str:
    """Case/whitespace-insensitive fingerprint from source + company + title."""
    key = "|".join(part.lower().strip() for part in (job.source, job.company, job.title))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()
