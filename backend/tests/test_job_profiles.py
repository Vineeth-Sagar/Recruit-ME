"""Job-profile CRUD, ownership isolation, validation, activation."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/job-profiles"

SAMPLE = {
    "name": "Backend Intern",
    "target_roles": ["Backend Engineer", "SDE Intern"],
    "locations": ["Bengaluru", "Remote"],
    "job_types": ["Internship"],
    "must_have_skills": ["Python", "SQL"],
    "nice_to_have_skills": ["Docker"],
    "exclude_companies": ["Acme"],
    "watchlist_companies": ["Stripe"],
    "min_match_percent": 60,
    "min_salary": 0,
    "schedule_cron": "0 2 * * *",
    "timezone": "Asia/Kolkata",
}


async def test_create_list_get_roundtrip(client, auth_headers):
    h = await auth_headers("owner@example.com")

    r = await client.post(BASE, json=SAMPLE, headers=h)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["name"] == "Backend Intern"
    assert created["target_roles"] == ["Backend Engineer", "SDE Intern"]
    assert created["is_active"] is False
    assert created["big3_optin"] is False

    r = await client.get(BASE, headers=h)
    assert r.status_code == 200
    assert [p["id"] for p in r.json()] == [created["id"]]

    r = await client.get(f"{BASE}/{created['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["min_match_percent"] == 60


async def test_update_and_delete(client, auth_headers):
    h = await auth_headers("editor@example.com")
    pid = (await client.post(BASE, json=SAMPLE, headers=h)).json()["id"]

    r = await client.patch(
        f"{BASE}/{pid}", json={"name": "Renamed", "locations": ["Hyderabad"]}, headers=h
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"
    assert r.json()["locations"] == ["Hyderabad"]
    assert r.json()["target_roles"] == SAMPLE["target_roles"]  # untouched

    assert (await client.delete(f"{BASE}/{pid}", headers=h)).status_code == 204
    assert (await client.get(f"{BASE}/{pid}", headers=h)).status_code == 404


async def test_big3_optin_defaults_off_and_can_be_toggled(client, auth_headers):
    h = await auth_headers("big3@example.com")
    created = (await client.post(BASE, json=SAMPLE, headers=h)).json()
    assert created["big3_optin"] is False

    r = await client.patch(f"{BASE}/{created['id']}", json={"big3_optin": True}, headers=h)
    assert r.status_code == 200
    assert r.json()["big3_optin"] is True

    # untouched by a patch that doesn't mention it
    r = await client.patch(f"{BASE}/{created['id']}", json={"name": "Still On"}, headers=h)
    assert r.json()["big3_optin"] is True

    r = await client.patch(f"{BASE}/{created['id']}", json={"big3_optin": False}, headers=h)
    assert r.json()["big3_optin"] is False


async def test_create_with_big3_optin_true(client, auth_headers):
    h = await auth_headers("big3create@example.com")
    r = await client.post(BASE, json={**SAMPLE, "big3_optin": True}, headers=h)
    assert r.status_code == 201
    assert r.json()["big3_optin"] is True


async def test_activate_deactivate(client, auth_headers):
    h = await auth_headers("activator@example.com")
    pid = (await client.post(BASE, json=SAMPLE, headers=h)).json()["id"]

    r = await client.post(f"{BASE}/{pid}:activate", headers=h)
    assert r.status_code == 200 and r.json()["is_active"] is True

    r = await client.post(f"{BASE}/{pid}:deactivate", headers=h)
    assert r.status_code == 200 and r.json()["is_active"] is False


async def test_ownership_isolation(client, auth_headers):
    ha = await auth_headers("alice-jp@example.com")
    hb = await auth_headers("bob-jp@example.com")
    pid = (await client.post(BASE, json=SAMPLE, headers=ha)).json()["id"]

    assert (await client.get(f"{BASE}/{pid}", headers=hb)).status_code == 404
    assert (await client.patch(f"{BASE}/{pid}", json={"name": "x"}, headers=hb)).status_code == 404
    assert (await client.delete(f"{BASE}/{pid}", headers=hb)).status_code == 404
    assert (await client.get(BASE, headers=hb)).json() == []


async def test_validation_errors(client, auth_headers):
    h = await auth_headers("validator@example.com")
    assert (await client.post(BASE, json={"name": ""}, headers=h)).status_code == 422
    assert (
        await client.post(BASE, json={"name": "ok", "min_match_percent": 150}, headers=h)
    ).status_code == 422


async def test_requires_auth(client):
    assert (await client.get(BASE)).status_code == 401
    assert (await client.post(BASE, json=SAMPLE)).status_code == 401
