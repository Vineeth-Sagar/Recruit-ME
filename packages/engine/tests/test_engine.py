"""run_engine end to end with fake ports and fake scrapers."""

import json
from datetime import UTC, datetime

import pytest
from recruit_engine import run_engine
from recruit_engine.types import (
    EngineInput,
    JobPosting,
    ProfileSpec,
    ResumeParse,
)

pytestmark = pytest.mark.asyncio


class FakeSeen:
    def __init__(self, already: set[str] | None = None):
        self.seen = set(already or ())
        self.marked: list[str] = []

    def filter_new(self, tenant_id: str, hashes: list[str]) -> set[str]:
        return {h for h in hashes if h not in self.seen}

    def mark_seen(self, tenant_id: str, hashes: list[str]) -> None:
        self.marked.extend(hashes)


class FakeRL:
    def __init__(self) -> None:
        self.keys: list[str] = []

    async def acquire(self, key: str) -> None:
        self.keys.append(key)


class FakeLLM:
    def __init__(self, reply: str = "{}"):
        self.reply = reply

    async def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
        return self.reply


class FakeClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 6, tzinfo=UTC)


def _fetch_returning(*jobs: JobPosting):
    async def _f(spec, cred, rl, *, timeout_s):
        return list(jobs)

    return _f


async def _fetch_boom(spec, cred, rl, *, timeout_s):
    raise RuntimeError("wellfound exploded")


def _input(**over) -> EngineInput:
    base = dict(
        run_id="run-1",
        tenant_id="tenant-1",
        profile=ProfileSpec(
            profile_id="p1",
            target_roles=["Backend Engineer"],
            locations=["Bengaluru"],
            min_match_percent=50,
            watchlist_companies=["Watched Co"],
        ),
        resumes=[
            ResumeParse(resume_id="r1", parsed={"technical_skills": ["Python"]}, skills=["Python"])
        ],
        enabled_sources=["yc", "wellfound"],
    )
    base.update(over)
    return EngineInput(**base)


def _patch_scrapers(monkeypatch, mapping):
    monkeypatch.setattr("recruit_engine.engine.SCRAPERS", mapping)


async def test_happy_path_scrape_match_report(monkeypatch):
    yc_job = JobPosting(source="YC", company="Acme", title="Backend Engineer", description="Python")
    wf_job = JobPosting(
        source="Wellfound", company="Beta", title="Backend Engineer", description="Go"
    )
    _patch_scrapers(
        monkeypatch,
        {"yc": _fetch_returning(yc_job), "wellfound": _fetch_returning(wf_job)},
    )
    reply = json.dumps(
        {
            "0": {
                "match_percentage": 90,
                "matched_skills": ["Python"],
                "missing_skills": ["Kafka"],
                "why_good_fit": "great",
                "urgency": "HIGH",
            },
            "1": {
                "match_percentage": 20,
                "missing_skills": ["Go"],
                "why_good_fit": "no",
                "urgency": "LOW",
            },
        }
    )
    steps: list[tuple] = []

    async def on_step(name, status, detail):
        steps.append((name, status))

    res = await run_engine(
        _input(),
        seen=FakeSeen(),
        rate_limiter=FakeRL(),
        llm=FakeLLM(reply),
        clock=FakeClock(),
        on_step=on_step,
    )

    assert res.scraped == 2
    assert res.new == 2
    assert res.per_source["yc"]["status"] == "ok"
    assert res.per_source["wellfound"]["status"] == "ok"
    assert [m.match_percentage for m in res.matched] == [90]  # 20 is below the 50 threshold
    assert res.missing_skills_tally == {"Kafka": 1, "Go": 1}
    assert res.report_bytes and res.report_bytes[:2] == b"PK"  # xlsx zip magic
    assert ("match", "succeeded") in steps and ("report", "succeeded") in steps


async def test_one_source_fails_others_still_populate(monkeypatch):
    _patch_scrapers(
        monkeypatch,
        {
            "yc": _fetch_returning(
                JobPosting(source="YC", company="Acme", title="Backend Engineer")
            ),
            "wellfound": _fetch_boom,
        },
    )
    res = await run_engine(
        _input(), seen=FakeSeen(), rate_limiter=FakeRL(), llm=FakeLLM("{}"), clock=FakeClock()
    )
    assert res.per_source["yc"]["status"] == "ok"
    assert res.per_source["wellfound"]["status"] == "failed"
    assert "exploded" in res.per_source["wellfound"]["error"]
    assert res.scraped == 1


async def test_jobspy_skipped_unless_opted_in(monkeypatch):
    called = {"n": 0}

    async def jobspy(spec, cred, rl, *, timeout_s):
        called["n"] += 1
        return []

    _patch_scrapers(monkeypatch, {"jobspy": jobspy})
    res = await run_engine(
        _input(enabled_sources=["jobspy"]),
        seen=FakeSeen(),
        rate_limiter=FakeRL(),
        llm=FakeLLM("{}"),
        clock=FakeClock(),
    )
    assert res.per_source["jobspy"]["status"] == "skipped"
    assert called["n"] == 0

    res2 = await run_engine(
        _input(
            enabled_sources=["jobspy"],
            profile=ProfileSpec(
                profile_id="p1", target_roles=["x"], locations=["y"], big3_optin=True
            ),
        ),
        seen=FakeSeen(),
        rate_limiter=FakeRL(),
        llm=FakeLLM("{}"),
        clock=FakeClock(),
    )
    assert res2.per_source["jobspy"]["status"] == "ok"
    assert called["n"] == 1


async def test_already_seen_jobs_are_dropped(monkeypatch):
    from recruit_engine.dedupe import compute_external_hash

    j1 = JobPosting(source="YC", company="Acme", title="Backend Engineer")
    j2 = JobPosting(source="YC", company="Beta", title="Backend Engineer")
    _patch_scrapers(monkeypatch, {"yc": _fetch_returning(j1, j2)})

    seen = FakeSeen(already={compute_external_hash(j1)})
    res = await run_engine(
        _input(enabled_sources=["yc"]),
        seen=seen,
        rate_limiter=FakeRL(),
        llm=FakeLLM(json.dumps({"0": {"match_percentage": 99}})),
        clock=FakeClock(),
    )
    assert res.scraped == 2
    assert res.new == 1
    assert res.matched[0].job.company == "Beta"


async def test_rate_limiter_acquired_per_source(monkeypatch):
    _patch_scrapers(
        monkeypatch,
        {"yc": _fetch_returning(), "wellfound": _fetch_returning()},
    )
    rl = FakeRL()
    await run_engine(
        _input(), seen=FakeSeen(), rate_limiter=rl, llm=FakeLLM("{}"), clock=FakeClock()
    )
    assert rl.keys == ["yc:tenant-1", "wellfound:tenant-1"]
