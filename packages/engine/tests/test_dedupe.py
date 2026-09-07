"""compute_external_hash — URL-based, source-independent job fingerprint."""

from recruit_engine.dedupe import compute_external_hash
from recruit_engine.types import JobPosting


def _job(**kw) -> JobPosting:
    base = {"source": "Wellfound", "company": "Acme", "title": "SDE Intern"}
    base.update(kw)
    return JobPosting(**base)


def test_url_identity_ignores_scheme_host_case_www_query_and_trailing_slash():
    a = _job(url="https://www.Acme.com/jobs/42/?utm_source=x")
    b = _job(url="http://acme.com/jobs/42")
    assert compute_external_hash(a) == compute_external_hash(b)


def test_source_does_not_affect_the_hash():
    # jobspy reports `source` inconsistently run-to-run — it must not matter.
    a = _job(source="LinkedIn", url="https://acme.com/jobs/42")
    b = _job(source="linkedin,indeed,glassdoor", url="https://acme.com/jobs/42")
    assert compute_external_hash(a) == compute_external_hash(b)


def test_distinct_urls_are_distinct():
    assert compute_external_hash(_job(url="https://acme.com/jobs/1")) != compute_external_hash(
        _job(url="https://acme.com/jobs/2")
    )


def test_no_url_falls_back_to_company_title_location():
    a = _job(company="Acme Corp", title="SDE Intern", location="Bengaluru")
    b = _job(company=" ACME corp", title="sde intern ", location=" bengaluru")
    assert compute_external_hash(a) == compute_external_hash(b)
    # same posting, different city -> different opening
    assert compute_external_hash(_job(location="Bengaluru")) != compute_external_hash(
        _job(location="Hyderabad")
    )
    assert compute_external_hash(_job(title="SDE")) != compute_external_hash(_job(title="PM"))


def test_hash_is_deterministic_and_hex():
    h = compute_external_hash(_job(url="https://acme.com/jobs/9"))
    assert h == compute_external_hash(_job(url="https://acme.com/jobs/9"))
    assert len(h) == 40 and all(c in "0123456789abcdef" for c in h)
