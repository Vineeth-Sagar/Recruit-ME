"""/api/v1/runs — 202 + idempotency, list/filter, detail, cancel, ownership, SSE."""

from __future__ import annotations

from datetime import UTC, datetime

from recruit_api.models.job_profile import JobProfile
from recruit_api.models.run import Run, RunStatus, RunStep

RUNS = "/api/v1/runs"


async def _profile(db, user_id, name="P") -> JobProfile:
    p = JobProfile(user_id=user_id, name=name, target_roles=["x"], locations=["y"])
    db.add(p)
    await db.flush()
    return p


async def test_create_returns_202_and_enqueues(client, login, db_session, enqueued):
    h, user = await login("runner@example.com")
    p = await _profile(db_session, user.id)

    r = await client.post(RUNS, json={"job_profile_id": str(p.id)}, headers=h)
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "queued" and body["trigger"] == "manual"
    assert enqueued == [("execute_run", body["id"])]


async def test_idempotency_key_dedupes(client, login, db_session, enqueued):
    h, user = await login("idem-run@example.com")
    p = await _profile(db_session, user.id)

    r1 = await client.post(
        RUNS, json={"job_profile_id": str(p.id)}, headers={**h, "Idempotency-Key": "abc-123"}
    )
    assert r1.status_code == 202
    r2 = await client.post(
        RUNS, json={"job_profile_id": str(p.id)}, headers={**h, "Idempotency-Key": "abc-123"}
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == r1.json()["id"]
    assert enqueued == [("execute_run", r1.json()["id"])]


async def test_create_for_foreign_profile_404(client, login, db_session):
    _, owner = await login("owner-run@example.com")
    hb, _ = await login("other-run@example.com")
    p = await _profile(db_session, owner.id)
    assert (
        await client.post(RUNS, json={"job_profile_id": str(p.id)}, headers=hb)
    ).status_code == 404


async def test_list_and_filter(client, login, db_session):
    h, user = await login("lister@example.com")
    p1 = await _profile(db_session, user.id, "P1")
    p2 = await _profile(db_session, user.id, "P2")
    db_session.add(
        Run(user_id=user.id, job_profile_id=p1.id, status=RunStatus.succeeded, idempotency_key="k1")
    )
    db_session.add(
        Run(user_id=user.id, job_profile_id=p2.id, status=RunStatus.failed, idempotency_key="k2")
    )
    await db_session.flush()

    assert (await client.get(RUNS, headers=h)).json()["total"] == 2
    r = await client.get(f"{RUNS}?status=failed", headers=h)
    assert r.json()["total"] == 1 and r.json()["items"][0]["status"] == "failed"
    assert (await client.get(f"{RUNS}?profile={p1.id}", headers=h)).json()["total"] == 1


async def test_detail_includes_steps(client, login, db_session):
    h, user = await login("detail@example.com")
    p = await _profile(db_session, user.id)
    run = Run(user_id=user.id, job_profile_id=p.id, status=RunStatus.running, idempotency_key="kd")
    db_session.add(run)
    await db_session.flush()
    db_session.add(
        RunStep(
            run_id=run.id,
            name="scrape:yc",
            status="succeeded",
            detail={"found": 3},
            at=datetime.now(UTC),
        )
    )
    await db_session.flush()

    r = await client.get(f"{RUNS}/{run.id}", headers=h)
    assert r.status_code == 200
    assert r.json()["steps"][0]["name"] == "scrape:yc"


async def test_cancel(client, login, db_session):
    h, user = await login("canceller@example.com")
    p = await _profile(db_session, user.id)
    run = Run(user_id=user.id, job_profile_id=p.id, status=RunStatus.queued, idempotency_key="kc")
    db_session.add(run)
    await db_session.flush()

    r = await client.post(f"{RUNS}/{run.id}:cancel", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    r = await client.post(f"{RUNS}/{run.id}:cancel", headers=h)  # idempotent
    assert r.status_code == 200 and r.json()["status"] == "cancelled"


async def test_ownership_isolation(client, login, db_session):
    ha, ua = await login("run-a@example.com")
    hb, _ = await login("run-b@example.com")
    p = await _profile(db_session, ua.id)
    run = Run(user_id=ua.id, job_profile_id=p.id, status=RunStatus.queued, idempotency_key="ko")
    db_session.add(run)
    await db_session.flush()

    assert (await client.get(f"{RUNS}/{run.id}", headers=hb)).status_code == 404
    assert (await client.post(f"{RUNS}/{run.id}:cancel", headers=hb)).status_code == 404
    assert (await client.get(RUNS, headers=hb)).json()["total"] == 0


async def test_events_stream_for_terminal_run(client, login, db_session):
    h, user = await login("sse@example.com")
    p = await _profile(db_session, user.id)
    run = Run(
        user_id=user.id,
        job_profile_id=p.id,
        status=RunStatus.succeeded,
        idempotency_key="ke",
        stats={"matched": 2},
    )
    db_session.add(run)
    await db_session.flush()

    r = await client.get(f"{RUNS}/{run.id}/events", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in r.text
