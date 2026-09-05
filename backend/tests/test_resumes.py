"""Résumé upload validation + the parse task (success, image-only, LLM error)."""

from __future__ import annotations

import pytest
from recruit_worker.tasks.parse_resume import parse_resume

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/resumes"


def _files(data: bytes, name: str = "cv.pdf", mime: str = "application/pdf"):
    return {"file": (name, data, mime)}


async def test_upload_stores_and_enqueues(
    client, auth_headers, pdf_with_text, object_store, enqueued
):
    h = await auth_headers("uploader@example.com")

    r = await client.post(BASE, files=_files(pdf_with_text), headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "uploaded"
    assert body["size_bytes"] == len(pdf_with_text)
    assert body["parse"] is None

    # bytes landed in object storage, and a parse job was queued
    assert await object_store.get(f"resumes/{body['user_id']}/{body['id']}.pdf") == pdf_with_text
    assert enqueued == [("parse_resume", body["id"])]


async def test_upload_rejects_non_pdf(client, auth_headers):
    h = await auth_headers("badfile@example.com")
    r = await client.post(
        BASE, files=_files(b"just some text", name="cv.txt", mime="text/plain"), headers=h
    )
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "unsupported_media_type"


async def test_ownership_isolation(client, auth_headers, pdf_with_text):
    ha = await auth_headers("owner-r@example.com")
    hb = await auth_headers("other-r@example.com")
    rid = (await client.post(BASE, files=_files(pdf_with_text), headers=ha)).json()["id"]

    assert (await client.get(f"{BASE}/{rid}", headers=hb)).status_code == 404
    assert (await client.delete(f"{BASE}/{rid}", headers=hb)).status_code == 404


async def test_delete_removes_object(client, auth_headers, pdf_with_text, object_store):
    h = await auth_headers("deleter@example.com")
    body = (await client.post(BASE, files=_files(pdf_with_text), headers=h)).json()
    key = f"resumes/{body['user_id']}/{body['id']}.pdf"
    assert await object_store.get(key) == pdf_with_text

    assert (await client.delete(f"{BASE}/{body['id']}", headers=h)).status_code == 204
    from recruit_api.services.object_store import ObjectNotFound

    with pytest.raises(ObjectNotFound):
        await object_store.get(key)


async def test_parse_task_success(client, auth_headers, pdf_with_text, worker_ctx):
    h = await auth_headers("parseok@example.com")
    rid = (await client.post(BASE, files=_files(pdf_with_text), headers=h)).json()["id"]

    await parse_resume(worker_ctx, rid)

    r = await client.get(f"{BASE}/{rid}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "parsed"
    assert body["parse"] is not None
    assert body["parse"]["model"] == "test-model"
    assert "Python" in body["parse"]["skills"]


async def test_parse_task_image_only_pdf_fails_cleanly(
    client, auth_headers, pdf_no_text, worker_ctx
):
    h = await auth_headers("parseimg@example.com")
    rid = (await client.post(BASE, files=_files(pdf_no_text), headers=h)).json()["id"]

    await parse_resume(worker_ctx, rid)  # must not raise

    body = (await client.get(f"{BASE}/{rid}", headers=h)).json()
    assert body["status"] == "failed"
    assert "text" in body["parse_error"].lower()
    assert body["parse"] is None


async def test_link_resume_to_profile(client, auth_headers, pdf_with_text):
    h = await auth_headers("linker@example.com")
    rid = (await client.post(BASE, files=_files(pdf_with_text), headers=h)).json()["id"]
    pid = (
        await client.post("/api/v1/job-profiles", json={"name": "P"}, headers=h)
    ).json()["id"]

    r = await client.patch(f"{BASE}/{rid}", json={"job_profile_id": pid}, headers=h)
    assert r.status_code == 200
    assert r.json()["job_profile_id"] == pid

    # unlink
    r = await client.patch(f"{BASE}/{rid}", json={"job_profile_id": None}, headers=h)
    assert r.status_code == 200 and r.json()["job_profile_id"] is None

    # cannot link to someone else's profile
    hb = await auth_headers("linker-b@example.com")
    pid_b = (
        await client.post("/api/v1/job-profiles", json={"name": "PB"}, headers=hb)
    ).json()["id"]
    r = await client.patch(f"{BASE}/{rid}", json={"job_profile_id": pid_b}, headers=h)
    assert r.status_code == 404


async def test_parse_task_llm_garbage_marks_failed(client, auth_headers, pdf_with_text, worker_ctx):
    class _Garbage:
        async def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
            return "sorry, I cannot do that"

    worker_ctx["llm"] = _Garbage()

    h = await auth_headers("parsebad@example.com")
    rid = (await client.post(BASE, files=_files(pdf_with_text), headers=h)).json()["id"]

    await parse_resume(worker_ctx, rid)

    body = (await client.get(f"{BASE}/{rid}", headers=h)).json()
    assert body["status"] == "failed"
