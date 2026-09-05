"""
dedupe.py  (← job_hunter/deduplicator.py)
SQLite-backed store to track jobs already seen, preventing duplicates.

Phase 4.1: logic unchanged. In Phase 4.4 the storage moves behind the
``SeenStore`` port (a Postgres table scoped by ``user_id``) and this SQLite
default disappears; tests already inject ``DB_PATH``.
"""

import hashlib
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "_local_seen_jobs.db"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            job_hash TEXT PRIMARY KEY,
            company   TEXT,
            title     TEXT,
            source    TEXT,
            first_seen DATE DEFAULT (date('now'))
        )
    """)
    conn.commit()
    return conn


def _job_hash(job: dict) -> str:
    """Create a stable hash from company + title + source."""
    key = f"{job.get('company', '').lower().strip()}|{job.get('title', '').lower().strip()}|{job.get('source', '').lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()


def filter_new_jobs(jobs: list[dict]) -> list[dict]:
    """Return only jobs not seen before."""
    conn = _get_connection()
    cur = conn.cursor()
    new_jobs = []
    for job in jobs:
        h = _job_hash(job)
        cur.execute("SELECT 1 FROM seen_jobs WHERE job_hash = ?", (h,))
        if cur.fetchone() is None:
            new_jobs.append(job)
    conn.close()
    return new_jobs


def mark_jobs_seen(jobs: list[dict]):
    """Mark a list of jobs as seen in the database."""
    conn = _get_connection()
    for job in jobs:
        h = _job_hash(job)
        conn.execute(
            "INSERT OR IGNORE INTO seen_jobs (job_hash, company, title, source) VALUES (?,?,?,?)",
            (h, job.get("company", ""), job.get("title", ""), job.get("source", "")),
        )
    conn.commit()
    conn.close()


def get_seen_count() -> int:
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM seen_jobs")
    count = cur.fetchone()[0]
    conn.close()
    return count


def clear_old_entries(days: int = 60):
    """Remove entries older than N days to keep DB lean."""
    conn = _get_connection()
    conn.execute("DELETE FROM seen_jobs WHERE first_seen < date('now', ?)", (f"-{days} days",))
    conn.commit()
    conn.close()
