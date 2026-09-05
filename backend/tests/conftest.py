"""Test harness: a real Postgres (testcontainers unless TEST_DATABASE_URL is
set), migrations applied once, each test in a rolled-back transaction."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

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
async def db_session(_engine) -> AsyncIterator[AsyncSession]:
    async with _engine.connect() as conn:
        txn = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await txn.rollback()


@pytest.fixture
def sent_emails() -> list[dict[str, str]]:
    """Populated with every email the app 'sends' during a test."""
    return []


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, sent_emails: list[dict[str, str]]
) -> AsyncIterator[AsyncClient]:
    from recruit_api.db import get_db
    from recruit_api.main import create_app
    from recruit_api.security.deps import get_email_sender

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    class _CaptureSender:
        async def send(self, *, to: str, subject: str, html: str) -> None:
            sent_emails.append({"to": to, "subject": subject, "html": html})

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_email_sender] = lambda: _CaptureSender()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── helpers ──────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def make_user(db_session: AsyncSession):
    """Create a user row directly (bypassing signup email)."""
    from recruit_api.models.user import User, UserRole, UserStatus
    from recruit_api.security.passwords import hash_password

    created: list[User] = []

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
        created.append(user)
        return user

    return _make


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, make_user):
    """(email) -> Authorization header dict for a logged-in active user."""

    async def _for(email: str, password: str = "password123", **kw):
        await make_user(email, password, **kw)
        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _for
