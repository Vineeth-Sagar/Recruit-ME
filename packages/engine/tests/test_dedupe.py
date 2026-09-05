"""
Unit tests for recruit_engine.dedupe  (← job_hunter/deduplicator.py).

Each test runs against a throwaway SQLite file via the `_isolated_db` fixture,
so the suite never touches any real dedup state.
"""

import pytest
from recruit_engine import dedupe


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(dedupe, "DB_PATH", tmp_path / "seen_jobs_test.db")


def test_job_hash_is_case_and_whitespace_insensitive():
    job1 = {"company": "Acme Corp", "title": "SDE Intern", "source": "LinkedIn"}
    job2 = {"company": " acme corp ", "title": " sde intern ", "source": "linkedin"}
    assert dedupe._job_hash(job1) == dedupe._job_hash(job2)


def test_job_hash_differs_for_different_jobs():
    job1 = {"company": "Acme", "title": "SDE", "source": "LinkedIn"}
    job2 = {"company": "Acme", "title": "PM", "source": "LinkedIn"}
    assert dedupe._job_hash(job1) != dedupe._job_hash(job2)


def test_filter_new_jobs_then_mark_seen_roundtrip():
    jobs = [
        {"company": "Acme", "title": "SDE", "source": "LinkedIn"},
        {"company": "Globex", "title": "PM", "source": "Indeed"},
    ]

    assert dedupe.filter_new_jobs(jobs) == jobs

    dedupe.mark_jobs_seen(jobs)
    assert dedupe.filter_new_jobs(jobs) == []

    fresh = [{"company": "Initech", "title": "QA", "source": "Wellfound"}]
    assert dedupe.filter_new_jobs(jobs + fresh) == fresh


def test_get_seen_count_reflects_marked_jobs():
    assert dedupe.get_seen_count() == 0
    dedupe.mark_jobs_seen([{"company": "Acme", "title": "SDE", "source": "LinkedIn"}])
    assert dedupe.get_seen_count() == 1


def test_clear_old_entries_does_not_remove_todays_entries():
    dedupe.mark_jobs_seen([{"company": "Acme", "title": "SDE", "source": "LinkedIn"}])
    dedupe.clear_old_entries(days=60)
    assert dedupe.get_seen_count() == 1
