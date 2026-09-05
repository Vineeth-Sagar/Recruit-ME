"""Role guards, account suspension, and per-caller data isolation."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

ADMIN_USERS = "/api/v1/admin/users"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/me"


async def test_regular_user_cannot_reach_admin(client, auth_headers):
    headers = await auth_headers("plainuser@example.com")
    r = await client.get(ADMIN_USERS, headers=headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


async def test_admin_can_list_users(client, auth_headers):
    from recruit_api.models.user import UserRole

    headers = await auth_headers("root@example.com", role=UserRole.admin)
    r = await client.get(ADMIN_USERS, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert {"items", "total", "page", "page_size"} <= body.keys()


async def test_admin_can_suspend_and_suspension_blocks_access(client, auth_headers, make_user):
    from recruit_api.models.user import UserRole

    admin_headers = await auth_headers("admin2@example.com", role=UserRole.admin)
    victim = await make_user("victim@example.com", "victimpass1")

    # victim can log in and read /me beforehand
    login = await client.post(
        LOGIN, json={"email": "victim@example.com", "password": "victimpass1"}
    )
    assert login.status_code == 200
    victim_token = login.json()["access_token"]
    assert (
        await client.get(ME, headers={"Authorization": f"Bearer {victim_token}"})
    ).status_code == 200

    # suspend
    r = await client.post(f"{ADMIN_USERS}/{victim.id}:suspend", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "suspended"

    # existing access token now rejected, and re-login is forbidden
    assert (
        await client.get(ME, headers={"Authorization": f"Bearer {victim_token}"})
    ).status_code == 403
    assert (
        await client.post(LOGIN, json={"email": "victim@example.com", "password": "victimpass1"})
    ).status_code == 403


async def test_me_returns_only_the_caller(client, auth_headers, make_user):
    await make_user("other@example.com")
    headers = await auth_headers("self@example.com")
    r = await client.get(ME, headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "self@example.com"


async def test_missing_and_garbage_tokens_are_401(client):
    assert (await client.get(ME)).status_code == 401
    assert (await client.get(ME, headers={"Authorization": "Bearer not-a-jwt"})).status_code == 401
