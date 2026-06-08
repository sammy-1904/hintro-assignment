"""
Test configuration and shared fixtures.

Uses an in-memory SQLite database for fast, isolated tests.
The get_db dependency is overridden so tests never touch PostgreSQL.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

# In-memory SQLite — no PostgreSQL needed for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="function")
async def db_session():
    """Create a fresh in-memory DB for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession):
    """HTTP test client with DB dependency overridden."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient) -> str:
    """Register a user and return the JWT access token."""
    await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123",
    })
    resp = await client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123",
    })
    return resp.json()["data"]["access_token"]
