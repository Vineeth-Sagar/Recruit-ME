"""Account self-service: change password, change email (confirm-by-link), delete."""

from __future__ import annotations

import re

import pytest
from recruit_api.models.job_profile import JobProfile
from recruit_api.models.site_credential import SiteCredential
from recruit_api.services.object_store import ObjectNotFound
from sqlalchemy import func, select

pytestmark = pytest.mark.asyncio

PASSWORD = "/api/v1/me/password"
EMAIL = "/api/v1/me/email"
CONFIRM = "/api/v1/auth/confirm-email-change"
ME = "/api/v1/me"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"


def _token(html: str) -> str:
    m = re.search(r"token=([A-Za-z0-9_\-]+)", html)
    assert m, html
    return m.group(1)


# ── change password ─────────────────────────────────────────────────────


async def test_change_password_rejects_wrong_current(client, login):
    headers, _ = await login("cp-wrong@example.com")
    r = await client.post(
        PASSWORD,
        json={"current_password": "nope", "new_password": "brandnewpass1"},
        headers=headers,
    )
    assert r.status_code == 401


async def test_change_password_revokes_sessions_and_rotates_credential(client, login):
    headers, _ = await login("cp-ok@example.com", "originalpass1")
    stale_refresh = client.cookies.get("recruit_refresh")

    r = await client.post(
        PASSWORD,
        json={"current_password": "originalpass1", "new_password": "a-fresh-secret9"},
        headers=headers,
    )
    assert r.status_code == 204

    # the refresh token issued at login no longer works
    bad = await client.post(REFRESH, cookies={"recruit_refresh": stale_refresh})
    assert bad.status_code == 401

    # old password is dead, new one works
    assert (
        await client.post(LOGIN, json={"email": "cp-ok@example.com", "password": "originalpass1"})
    ).status_code == 401
    assert (
        await client.post(LOGIN, json={"email": "cp-ok@example.com", "password": "a-fresh-secret9"})
    ).status_code == 200


async def test_change_password_requires_auth(client):
    r = await client.post(PASSWORD, json={"current_password": "x", "new_password": "yyyyyyyy"})
    assert r.status_code == 401


# ── change email ────────────────────────────────────────────────────────


async def test_email_change_rejects_wrong_password(client, login):
    headers, _ = await login("ec-wrong@example.com")
    r = await client.post(
        EMAIL, json={"new_email": "new@example.com", "current_password": "nope"}, headers=headers
    )
    assert r.status_code == 401


async def test_email_change_rejects_taken_address(client, login):
    await login("taken@example.com")
    headers, _ = await login("ec-dup@example.com", "originalpass1")
    r = await client.post(
        EMAIL,
        json={"new_email": "taken@example.com", "current_password": "originalpass1"},
        headers=headers,
    )
    assert r.status_code == 409


async def test_email_change_confirm_flow(client, login, sent_emails):
    headers, user = await login("ec-ok@example.com", "originalpass1")
    stale_refresh = client.cookies.get("recruit_refresh")

    r = await client.post(
        EMAIL,
        json={"new_email": "moved@example.com", "current_password": "originalpass1"},
        headers=headers,
    )
    assert r.status_code == 202
    assert sent_emails and sent_emails[-1]["to"] == "moved@example.com"

    r = await client.post(CONFIRM, json={"token": _token(sent_emails[-1]["html"])})
    assert r.status_code == 204

    me = await client.get(ME, headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "moved@example.com"

    # email change is a credential change -> old sessions die
    assert (
        await client.post(REFRESH, cookies={"recruit_refresh": stale_refresh})
    ).status_code == 401
    assert (
        await client.post(LOGIN, json={"email": "moved@example.com", "password": "originalpass1"})
    ).status_code == 200


async def test_email_confirm_rejects_bad_token(client):
    assert (await client.post(CONFIRM, json={"token": "not-a-real-token"})).status_code == 401


# ── delete account ─────────────────────────────────────────────────────


async def test_delete_account_rejects_wrong_password(client, login):
    headers, _ = await login("del-wrong@example.com")
    r = await client.request(
        "DELETE",
        ME,
        json={"password": "nope", "confirm_email": "del-wrong@example.com"},
        headers=headers,
    )
    assert r.status_code == 401


async def test_delete_account_rejects_confirmation_mismatch(client, login):
    headers, _ = await login("del-mismatch@example.com", "originalpass1")
    r = await client.request(
        "DELETE",
        ME,
        json={"password": "originalpass1", "confirm_email": "someone-else@example.com"},
        headers=headers,
    )
    assert r.status_code == 401


async def test_delete_account_cascades_and_wipes_storage(client, login, db_session, object_store):
    headers, user = await login("del-ok@example.com", "originalpass1")

    assert (
        await client.post("/api/v1/job-profiles", json={"name": "P"}, headers=headers)
    ).status_code == 201
    await client.put(
        "/api/v1/me/site-credentials/linkedin",
        json={"auth_type": "cookie", "secret": {"li_at": "x"}},
        headers=headers,
    )
    resume_key = f"resumes/{user.id}/cv.pdf"
    report_key = f"reports/{user.id}/run.xlsx"
    await object_store.put(resume_key, b"%PDF-1.4", content_type="application/pdf")
    await object_store.put(report_key, b"xlsx", content_type="application/octet-stream")

    r = await client.request(
        "DELETE",
        ME,
        json={"password": "originalpass1", "confirm_email": "del-ok@example.com"},
        headers=headers,
    )
    assert r.status_code == 204

    # the still-valid access token stops working on its next request
    assert (await client.get(ME, headers=headers)).status_code == 401

    # tenant rows are gone via FK cascade
    assert (
        await db_session.scalar(
            select(func.count()).select_from(JobProfile).where(JobProfile.user_id == user.id)
        )
    ) == 0
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(SiteCredential)
            .where(SiteCredential.user_id == user.id)
        )
    ) == 0

    # object storage prefixes are wiped
    for key in (resume_key, report_key):
        with pytest.raises(ObjectNotFound):
            await object_store.get(key)


async def test_delete_account_requires_auth(client):
    r = await client.request("DELETE", ME, json={"password": "x", "confirm_email": "a@example.com"})
    assert r.status_code == 401
