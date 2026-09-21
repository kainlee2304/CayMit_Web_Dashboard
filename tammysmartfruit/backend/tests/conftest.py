"""
Pytest Fixtures for Backend Core Foundation Tests
Supports both PostgreSQL and SQLite fallback seamlessly.
"""

import os
from typing import AsyncGenerator
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure tests use SQLite fallback immediately
sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tammysmartfruit.db"))
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{sqlite_path.replace(os.sep, '/')}"

from app.main import app
from app.core.database import get_db, init_database_schema_and_seeds
import app.core.database as db_module

@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_db():
    await db_module.switch_to_sqlite()
    await init_database_schema_and_seeds()

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_module.AsyncSessionLocal() as session:
        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        yield session
        app.dependency_overrides.pop(get_db, None)

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
