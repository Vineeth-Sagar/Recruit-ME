"""/api/v1/matches — filter, sort, mark saved/applied/dismissed, ownership."""

from __future__ import annotations

from recruit_api.models.run import JobMatch

M = "/api/v1/matches"


async def _match(db, user_id, **kw) -> JobMatch:
    base = dict(
        user_id=user_id,
        external_hash=kw.pop("external_hash", "h"),
        source="YC",
        company=kw.pop("company", "Acme"),
        title=kw.pop("title", "Backend Engineer"),
        match_percentage=kw.pop("match_percentage", 50),
    )
    base.update(kw)
    m = JobMatch(**base)
    db.add(m)
    await db.flush()
    return m


async def test_list_sorted_by_match_desc(client, login, db_session):
    h, user = await login("m-list@example.com")
    await _match(db_session, user.id, match_percentage=40, external_hash="a")
    await _match(db_session, user.id, match_percentage=90, external_hash="b")
    await _match(db_session, user.id, match_percentage=70, external_hash="c")

    r = await client.get(M, headers=h)
    assert r.status_code == 200
    assert [m["match_percentage"] for m in r.json()["items"]] == [90, 70, 40]


async def test_filters(client, login, db_session):
    h, user = await login("m-filter@example.com")
    await _match(db_session, user.id, match_percentage=30, company="Globex", external_hash="a")
    await _match(db_session, user.id, match_percentage=85, company="Acme Corp", external_hash="b")

    assert (await client.get(f"{M}?min_match=50", headers=h)).json()["total"] == 1
    assert (await client.get(f"{M}?q=acme", headers=h)).json()["items"][0]["company"] == "Acme Corp"
    assert (await client.get(f"{M}?status=new", headers=h)).json()["total"] == 2


async def test_patch_status(client, login, db_session):
    h, user = await login("m-patch@example.com")
    m = await _match(db_session, user.id, external_hash="x")

    r = await client.patch(f"{M}/{m.id}", json={"status": "applied"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "applied" and r.json()["applied_at"] is not None

    r = await client.patch(f"{M}/{m.id}", json={"status": "dismissed"}, headers=h)
    assert r.json()["status"] == "dismissed"


async def test_ownership(client, login, db_session):
    ha, ua = await login("m-a@example.com")
    hb, _ = await login("m-b@example.com")
    m = await _match(db_session, ua.id, external_hash="z")

    assert (await client.get(M, headers=hb)).json()["total"] == 0
    assert (
        await client.patch(f"{M}/{m.id}", json={"status": "saved"}, headers=hb)
    ).status_code == 404
