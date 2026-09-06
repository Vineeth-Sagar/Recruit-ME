"""Test harness: a real Postgres (testcontainers unless TEST_DATABASE_URL is
set), migrations applied once, each test in a rolled-back transaction. Object
storage and the job queue are in-memory fakes shared with the worker fixtures."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    env_url = os.environ.get("TEST_DATABASE_URL")
    if env_url:
        yield env_url
        return
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="session", autouse=True)
def _configure_settings(database_url: str) -> Iterator[None]:
    os.environ["ENV"] = "test"
    os.environ["DATABASE_URL"] = database_url
    from recruit_api.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def _migrate(_configure_settings: None, database_url: str) -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture(scope="session")
async def _engine(database_url: str):
    engine = create_async_engine(database_url, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def _conn(_engine):
    """One connection + outer transaction per test; everything rolls back."""
    async with _engine.connect() as conn:
        txn = await conn.begin()
        try:
            yield conn
        finally:
            await txn.rollback()


@pytest.fixture
def sessionmaker_bound(_conn) -> async_sessionmaker[AsyncSession]:
    """Sessions that join the test's transaction (commits become savepoints)."""
    return async_sessionmaker(
        bind=_conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


@pytest_asyncio.fixture
async def db_session(sessionmaker_bound) -> AsyncIterator[AsyncSession]:
    async with sessionmaker_bound() as session:
        yield session


@pytest.fixture
def shared_sessionmaker(db_session):
    """A callable that hands out the test's single session without closing it —
    lets worker tasks (`async with sessionmaker() as db`) share the txn."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _ctx():
        yield db_session

    return _ctx


@pytest.fixture
def sent_emails() -> list[dict[str, str]]:
    return []


@pytest.fixture
def object_store():
    from recruit_api.services.object_store import InMemoryObjectStore

    return InMemoryObjectStore()


@pytest.fixture
def enqueued() -> list[tuple]:
    """Every (fn, *args) the app enqueues during a test."""
    return []


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    sent_emails: list[dict[str, str]],
    object_store,
    enqueued: list[tuple],
) -> AsyncIterator[AsyncClient]:
    from recruit_api.db import get_db
    from recruit_api.main import create_app
    from recruit_api.security.deps import get_email_sender, get_enqueue_dep, get_object_store

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    class _CaptureSender:
        async def send(self, *, to: str, subject: str, html: str) -> None:
            sent_emails.append({"to": to, "subject": subject, "html": html})

    async def _fake_enqueue(fn: str, *args) -> None:
        enqueued.append((fn, *args))

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_email_sender] = lambda: _CaptureSender()
    app.dependency_overrides[get_object_store] = lambda: object_store
    app.dependency_overrides[get_enqueue_dep] = lambda: _fake_enqueue
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def worker_ctx(shared_sessionmaker, object_store):
    """ctx dict for calling worker tasks directly, sharing the test's DB txn
    and object store. `llm` defaults to a canned parser; override per test."""

    class _CannedLLM:
        payload = (
            '{"name": "Test User", "technical_skills": ["Python", "FastAPI"], '
            '"languages": ["Python"], "frameworks": ["FastAPI"], "tools": ["Docker"], '
            '"summary": "A tester."}'
        )

        async def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
            return self.payload

    return {
        "sessionmaker": shared_sessionmaker,
        "object_store": object_store,
        "llm": _CannedLLM(),
        "llm_model": "test-model",
    }


class _CaptureEmail:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    async def send(self, *, to: str, subject: str, html: str) -> None:
        self.sent.append({"to": to, "subject": subject, "html": html})


class _NoopRateLimiter:
    def __init__(self) -> None:
        self.keys: list[str] = []

    async def acquire(self, key: str) -> None:
        self.keys.append(key)


@pytest.fixture
def execute_run_ctx(shared_sessionmaker, object_store):
    """ctx for calling recruit_worker.tasks.execute_run directly. Fields are
    swappable per test (llm, object_store, email_sender, rate_limiter)."""

    class _CannedLLM:
        reply = "{}"

        async def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
            return self.reply

    return {
        "sessionmaker": shared_sessionmaker,
        "object_store": object_store,
        "email_sender": _CaptureEmail(),
        "rate_limiter": _NoopRateLimiter(),
        "llm": _CannedLLM(),
        "llm_model": "test-model",
        "worker_id": "test-worker",
    }


@pytest_asyncio.fixture
async def redis_client():
    """Real Redis (compose on 16379 db 1, or TEST_REDIS_URL), flushed per test."""
    import os

    from redis.asyncio import Redis

    url = os.environ.get("TEST_REDIS_URL", "redis://localhost:16379/1")
    client = Redis.from_url(url, decode_responses=False)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


# ── PDF byte helpers ─────────────────────────────────────────────────────


@pytest.fixture
def pdf_with_text() -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Test User\nSkills: Python, FastAPI, Docker, PostgreSQL")
    data: bytes = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def pdf_no_text() -> bytes:
    import fitz

    doc = fitz.open()
    doc.new_page()  # blank page, no text layer
    data: bytes = doc.tobytes()
    doc.close()
    return data


# ── user / auth helpers ──────────────────────────────────────────────────


@pytest_asyncio.fixture
async def make_user(db_session: AsyncSession):
    from recruit_api.models.user import User, UserRole, UserStatus
    from recruit_api.security.passwords import hash_password

    async def _make(
        email: str,
        password: str = "password123",
        *,
        role: UserRole = UserRole.user,
        status: UserStatus = UserStatus.active,
    ) -> User:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=email.split("@")[0],
            role=role,
            status=status,
        )
        db_session.add(user)
        await db_session.flush()
        return user

    return _make


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, make_user):
    async def _for(email: str, password: str = "password123", **kw):
        await make_user(email, password, **kw)
        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _for


@pytest_asyncio.fixture
async def login(client: AsyncClient, make_user):
    """(email) -> (headers, User). Use user.id (a real UUID) when building rows."""

    async def _login(email: str, password: str = "password123", **kw):
        user = await make_user(email, password, **kw)
        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        return headers, user

    return _login
