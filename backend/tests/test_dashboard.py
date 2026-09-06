"""/api/v1/dashboard/summary + /api/v1/matches/export.xlsx."""

from __future__ import annotations

from recruit_api.models.job_profile import JobProfile
from recruit_api.models.run import JobMatch, MatchStatus, Run, RunStatus

SUMMARY = "/api/v1/dashboard/summary"
EXPORT = "/api/v1/matches/export.xlsx"


async def _match(db, user_id, **kw) -> JobMatch:
    base = dict(
        user_id=user_id,
        external_hash=kw.pop("external_hash", "h"),
        source="YC",
        company=kw.pop("company", "Acme"),
        title=kw.pop("title", "Backend Engineer"),
        match_percentage=kw.pop("match_percentage", 60),
        missing_skills=kw.pop("missing_skills", []),
    )
    base.update(kw)
    m = JobMatch(**base)
    db.add(m)
    await db.flush()
    return m


async def test_summary_counts(client, login, db_session):
    h, user = await login("dash@example.com")
    p = JobProfile(user_id=user.id, name="P", target_roles=["x"], locations=["y"])
    db_session.add(p)
    await db_session.flush()
    db_session.add(
        Run(user_id=user.id, job_profile_id=p.id, status=RunStatus.succeeded, idempotency_key="r1")
    )
    db_session.add(
        Run(user_id=user.id, job_profile_id=p.id, status=RunStatus.failed, idempotency_key="r2")
    )
    db_session.add(
        Run(user_id=user.id, job_profile_id=p.id, status=RunStatus.queued, idempotency_key="r3")
    )
    await db_session.flush()

    await _match(
        db_session, user.id, external_hash="a", match_percentage=90, missing_skills=["Kafka", "Go"]
    )
    await _match(
        db_session, user.id, external_hash="b", match_percentage=40, missing_skills=["Kafka"]
    )
    m3 = await _match(db_session, user.id, external_hash="c", match_percentage=70)
    m3.status = MatchStatus.applied
    m4 = await _match(db_session, user.id, external_hash="d", match_percentage=55)
    m4.status = MatchStatus.applied
    await db_session.flush()

    r = await client.get(SUMMARY, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["runs_30d"] == 3
    assert body["last_run"]["status"] in {"queued", "succeeded", "failed"}
    assert body["matches_total"] == 4
    assert body["matches_new"] == 2
    assert body["applied_count"] == 2
    assert len(body["match_rate_series"]) == 14
    assert body["match_rate_series"][-1]["count"] == 4  # all created "today"
    assert body["top_missing_skills"][0] == {"skill": "Kafka", "n": 2}


async def test_summary_empty_account(client, login):
    h, _ = await login("dash-empty@example.com")
    r = await client.get(SUMMARY, headers=h)
    assert r.status_code == 200
    b = r.json()
    assert b["runs_30d"] == 0 and b["matches_total"] == 0 and b["last_run"] is None
    assert len(b["match_rate_series"]) == 14 and b["top_missing_skills"] == []


async def test_export_xlsx(client, login, db_session):
    h, user = await login("export@example.com")
    await _match(db_session, user.id, external_hash="a", match_percentage=88, company="Zeta")
    await _match(db_session, user.id, external_hash="b", match_percentage=30, company="Yotta")

    r = await client.get(EXPORT, headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment" in r.headers["content-disposition"]
    assert r.content[:2] == b"PK"  # xlsx is a zip

    # filter carries through
    r = await client.get(f"{EXPORT}?min_match=50", headers=h)
    assert r.status_code == 200 and r.content[:2] == b"PK"
