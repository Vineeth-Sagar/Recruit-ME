"""Sealed per-site credentials: the API only seals, the worker verifies/opens."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from recruit_api.config import get_settings
from recruit_api.models.site_credential import CredentialStatus, SiteCredential
from recruit_api.security.crypto import build_envelope
from recruit_worker.credentials import load_source_credentials
from recruit_worker.tasks.verify_credential import verify_credential
from sqlalchemy import select

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/me/site-credentials"
SRC = Path(__file__).resolve().parent.parent / "src" / "recruit_api"


async def _row(db, user_id, site="linkedin") -> SiteCredential:
    return await db.scalar(
        select(SiteCredential).where(SiteCredential.user_id == user_id, SiteCredential.site == site)
    )


async def test_put_seals_the_secret_and_never_echoes_it(client, login, db_session, enqueued):
    headers, user = await login("seal@example.com")

    r = await client.put(
        f"{BASE}/linkedin",
        json={"auth_type": "cookie", "secret": {"li_at": "AQEDSECRETVALUE"}, "label": "personal"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "secret" not in body and "secret_ciphertext" not in body
    assert body["site"] == "linkedin"
    assert body["status"] == "unverified"
    assert body["label"] == "personal"

    row = await _row(db_session, user.id)
    assert isinstance(row.secret_ciphertext, bytes) and row.secret_ciphertext
    assert b"AQEDSECRETVALUE" not in row.secret_ciphertext
    assert isinstance(row.nonce, bytes) and len(row.nonce) == 12
    assert row.key_version == 1

    assert ("verify_credential", str(row.id)) in enqueued


async def test_get_list_has_no_secret(client, login):
    headers, _ = await login("list@example.com")
    await client.put(
        f"{BASE}/wellfound",
        json={"auth_type": "api_key", "secret": {"api_key": "wf_live_xyz"}},
        headers=headers,
    )
    r = await client.get(BASE, headers=headers)
    assert r.status_code == 200
    (item,) = r.json()
    assert item["site"] == "wellfound"
    assert "secret" not in item
    assert set(item) == {
        "id",
        "site",
        "auth_type",
        "status",
        "label",
        "last_verified_at",
        "verify_error",
        "created_at",
        "updated_at",
    }


async def test_put_is_an_upsert_and_resets_status(client, login, db_session, worker_ctx):
    headers, user = await login("upsert@example.com")
    envelope = build_envelope(get_settings())
    ctx = {**worker_ctx, "envelope": envelope}

    await client.put(
        f"{BASE}/linkedin",
        json={"auth_type": "cookie", "secret": {"li_at": "first"}},
        headers=headers,
    )
    row = await _row(db_session, user.id)
    await verify_credential(ctx, str(row.id))
    await db_session.refresh(row)
    assert row.status == CredentialStatus.valid

    # a second PUT replaces the secret and knocks the row back to unverified
    await client.put(
        f"{BASE}/linkedin",
        json={"auth_type": "cookie", "secret": {"li_at": "second"}},
        headers=headers,
    )
    await db_session.refresh(row)
    assert row.status == CredentialStatus.unverified
    assert row.last_verified_at is None
    assert (
        envelope.decrypt(row.secret_ciphertext, row.nonce, row.key_version) == b'{"li_at":"second"}'
    )

    rows = list(
        await db_session.scalars(select(SiteCredential).where(SiteCredential.user_id == user.id))
    )
    assert len(rows) == 1  # upsert, not insert


async def test_verify_endpoint_re_enqueues(client, login, db_session, enqueued):
    headers, user = await login("reverify@example.com")
    await client.put(
        f"{BASE}/linkedin",
        json={"auth_type": "cookie", "secret": {"li_at": "x"}},
        headers=headers,
    )
    enqueued.clear()
    r = await client.post(f"{BASE}/linkedin:verify", headers=headers)
    assert r.status_code == 202
    row = await _row(db_session, user.id)
    assert ("verify_credential", str(row.id)) in enqueued


async def test_verify_missing_site_is_404(client, login):
    headers, _ = await login("missing@example.com")
    assert (await client.post(f"{BASE}/indeed:verify", headers=headers)).status_code == 404


async def test_delete(client, login, db_session):
    headers, user = await login("del@example.com")
    await client.put(
        f"{BASE}/glassdoor",
        json={"auth_type": "cookie", "secret": {"gdId": "g"}},
        headers=headers,
    )
    assert (await client.delete(f"{BASE}/glassdoor", headers=headers)).status_code == 204
    assert (await client.get(BASE, headers=headers)).json() == []
    assert await _row(db_session, user.id, "glassdoor") is None


async def test_credentials_are_per_tenant(client, login):
    ha, _ = await login("owner-cred@example.com")
    hb, _ = await login("other-cred@example.com")
    await client.put(
        f"{BASE}/linkedin",
        json={"auth_type": "cookie", "secret": {"li_at": "a"}},
        headers=ha,
    )
    assert (await client.get(BASE, headers=hb)).json() == []
    assert (await client.delete(f"{BASE}/linkedin", headers=hb)).status_code == 404


async def test_unknown_site_rejected_by_path_enum(client, login):
    headers, _ = await login("badsite@example.com")
    r = await client.put(
        f"{BASE}/monster",
        json={"auth_type": "cookie", "secret": {"x": "y"}},
        headers=headers,
    )
    assert r.status_code == 422


async def test_empty_secret_rejected(client, login):
    headers, _ = await login("emptysec@example.com")
    r = await client.put(
        f"{BASE}/linkedin",
        json={"auth_type": "cookie", "secret": {"li_at": "   "}},
        headers=headers,
    )
    assert r.status_code == 422


async def test_requires_auth(client):
    assert (await client.get(BASE)).status_code == 401


# ── worker: verify_credential structural check ───────────────────────────


async def test_verify_marks_valid_for_a_well_formed_cookie(client, login, db_session, worker_ctx):
    headers, user = await login("vgood@example.com")
    ctx = {**worker_ctx, "envelope": build_envelope(get_settings())}
    await client.put(
        f"{BASE}/linkedin",
        json={"auth_type": "cookie", "secret": {"li_at": "AQEDlooksreal"}},
        headers=headers,
    )
    row = await _row(db_session, user.id)
    await verify_credential(ctx, str(row.id))
    await db_session.refresh(row)
    assert row.status == CredentialStatus.valid
    assert row.verify_error == ""
    assert row.last_verified_at is not None


async def test_verify_marks_invalid_when_expected_key_missing(
    client, login, db_session, worker_ctx
):
    headers, user = await login("vbad@example.com")
    ctx = {**worker_ctx, "envelope": build_envelope(get_settings())}
    await client.put(
        f"{BASE}/linkedin",
        json={"auth_type": "cookie", "secret": {"jsessionid": "nope"}},
        headers=headers,
    )
    row = await _row(db_session, user.id)
    await verify_credential(ctx, str(row.id))
    await db_session.refresh(row)
    assert row.status == CredentialStatus.invalid
    assert "li_at" in row.verify_error


async def test_verify_missing_row_is_a_noop(worker_ctx):
    ctx = {**worker_ctx, "envelope": build_envelope(get_settings())}
    await verify_credential(ctx, str(uuid.uuid4()))  # must not raise


# ── worker: load_source_credentials ─────────────────────────────────────


async def test_load_source_credentials_decrypts_and_filters(client, login, db_session):
    headers, user = await login("loadcreds@example.com")
    envelope = build_envelope(get_settings())

    await client.put(
        f"{BASE}/wellfound",
        json={"auth_type": "api_key", "secret": {"api_key": "wf_key"}},
        headers=headers,
    )
    await client.put(
        f"{BASE}/linkedin",
        json={"auth_type": "cookie", "secret": {"li_at": "cookie-val"}},
        headers=headers,
    )
    # mark the linkedin row invalid — it should be skipped
    li = await _row(db_session, user.id, "linkedin")
    li.status = CredentialStatus.invalid
    await db_session.flush()

    creds = await load_source_credentials(db_session, user.id, envelope)
    assert [c.site for c in creds] == ["wellfound"]
    assert creds[0].auth_type == "api_key"
    assert creds[0].secret == {"api_key": "wf_key"}


async def test_load_source_credentials_skips_undecryptable_rows(login, db_session):
    _, user = await login("badcipher@example.com")
    db_session.add(
        SiteCredential(
            user_id=user.id,
            site="linkedin",
            auth_type="cookie",
            secret_ciphertext=b"garbage-not-a-valid-ciphertext",
            nonce=b"0" * 12,
            key_version=1,
        )
    )
    await db_session.flush()
    creds = await load_source_credentials(db_session, user.id, build_envelope(get_settings()))
    assert creds == []


# ── the decrypt path must not be reachable from a router ────────────────


async def test_routers_never_decrypt():
    offenders = []
    for p in (SRC / "routers").glob("*.py"):
        text = p.read_text(encoding="utf-8")
        if any(tok in text for tok in ("open_secret", "load_source_credentials", ".decrypt(")):
            offenders.append(p.name)
    assert offenders == [], f"router(s) reach the decrypt path: {offenders}"


async def test_api_credential_service_only_seals():
    text = (SRC / "services" / "site_credential_service.py").read_text(encoding="utf-8")
    assert ".encrypt(" in text
    assert ".decrypt(" not in text
    assert "open_secret" not in text
