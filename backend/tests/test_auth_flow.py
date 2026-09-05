"""signup -> verify -> login -> /me -> refresh rotation -> reuse detection -> logout."""

from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.asyncio

SIGNUP = "/api/v1/auth/signup"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
VERIFY = "/api/v1/auth/verify-email"
ME = "/api/v1/me"


def _token_from_email(html: str) -> str:
    m = re.search(r"token=([A-Za-z0-9_\-]+)", html)
    assert m, f"no token in email: {html}"
    return m.group(1)


async def test_full_auth_lifecycle(client, sent_emails):
    # signup
    r = await client.post(
        SIGNUP,
        json={"email": "alice@example.com", "password": "hunter2hunter", "full_name": "Alice"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["status"] == "pending_verification"
    assert body["role"] == "user"
    assert len(sent_emails) == 1

    # verify email
    token = _token_from_email(sent_emails[0]["html"])
    assert (await client.post(VERIFY, json={"token": token})).status_code == 204

    # login
    r = await client.post(LOGIN, json={"email": "alice@example.com", "password": "hunter2hunter"})
    assert r.status_code == 200, r.text
    access = r.json()["access_token"]
    assert r.json()["token_type"] == "bearer"
    assert "recruit_refresh" in client.cookies

    # /me with and without the bearer
    r = await client.get(ME, headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"
    assert r.json()["status"] == "active"

    assert (await client.get(ME)).status_code == 401

    # refresh rotates
    old_refresh = client.cookies["recruit_refresh"]
    r = await client.post(REFRESH)
    assert r.status_code == 200, r.text
    new_access = r.json()["access_token"]
    new_refresh = client.cookies["recruit_refresh"]
    assert new_refresh != old_refresh
    assert new_access != access

    # the newly rotated token still works
    r = await client.get(ME, headers={"Authorization": f"Bearer {new_access}"})
    assert r.status_code == 200

    # replaying the OLD refresh token = reuse -> 401 and the whole family dies
    client.cookies.set("recruit_refresh", old_refresh)
    assert (await client.post(REFRESH)).status_code == 401

    client.cookies.set("recruit_refresh", new_refresh)
    assert (await client.post(REFRESH)).status_code == 401


async def test_login_rejects_bad_password(client, make_user):
    await make_user("bob@example.com", "correcthorse")
    r = await client.post(LOGIN, json={"email": "bob@example.com", "password": "wrong"})
    assert r.status_code == 401


async def test_signup_duplicate_email_conflicts(client):
    payload = {"email": "dup@example.com", "password": "password123"}
    assert (await client.post(SIGNUP, json=payload)).status_code == 201
    r = await client.post(SIGNUP, json=payload)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


async def test_logout_invalidates_refresh(client, auth_headers):
    await auth_headers("carol@example.com")  # logs in; sets the refresh cookie
    assert (await client.post(LOGOUT)).status_code == 204
    assert (await client.post(REFRESH)).status_code == 401


async def test_password_reset_flow(client, make_user, sent_emails):
    await make_user("dave@example.com", "originalpass1")
    assert (
        await client.post("/api/v1/auth/forgot", json={"email": "dave@example.com"})
    ).status_code == 204
    assert (
        await client.post("/api/v1/auth/forgot", json={"email": "nobody@example.com"})
    ).status_code == 204  # no enumeration
    assert len(sent_emails) == 1

    token = _token_from_email(sent_emails[0]["html"])
    r = await client.post("/api/v1/auth/reset", json={"token": token, "password": "brandnewpass9"})
    assert r.status_code == 204

    assert (
        await client.post(LOGIN, json={"email": "dave@example.com", "password": "originalpass1"})
    ).status_code == 401
    assert (
        await client.post(LOGIN, json={"email": "dave@example.com", "password": "brandnewpass9"})
    ).status_code == 200
