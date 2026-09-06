"""compute_external_hash — stable, case/whitespace-insensitive job fingerprint."""

from recruit_engine.dedupe import compute_external_hash
from recruit_engine.types import JobPosting


def _job(**kw) -> JobPosting:
    base = {"source": "Wellfound", "company": "Acme", "title": "SDE Intern"}
    base.update(kw)
    return JobPosting(**base)


def test_hash_is_case_and_whitespace_insensitive():
    a = _job(source="Wellfound", company="Acme Corp", title="SDE Intern")
    b = _job(source="  wellfound ", company=" ACME corp", title="sde intern ")
    assert compute_external_hash(a) == compute_external_hash(b)


def test_hash_differs_for_different_jobs():
    assert compute_external_hash(_job(title="SDE")) != compute_external_hash(_job(title="PM"))
    assert compute_external_hash(_job(company="Acme")) != compute_external_hash(
        _job(company="Globex")
    )
    assert compute_external_hash(_job(source="YC Jobs")) != compute_external_hash(_job(source="HN"))


def test_hash_is_deterministic_and_hex():
    h = compute_external_hash(_job())
    assert h == compute_external_hash(_job())
    assert len(h) == 40 and all(c in "0123456789abcdef" for c in h)
