from __future__ import annotations

import os
import uuid

# Point the app at a throwaway DB before any app module is imported, since
# settings are loaded once at import time.
TEST_DB_PATH = f"/tmp/code_review_test_{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api import routes
from app.db.session import engine, init_db
from app.main import app
from tests.helpers import MockLLMClient


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _database():
    await init_db()
    yield
    await engine.dispose()
    for suffix in ("", "-wal", "-shm", "-journal"):
        path = TEST_DB_PATH + suffix
        if os.path.exists(path):
            os.remove(path)


@pytest.fixture
def mock_llm():
    return MockLLMClient()


@pytest_asyncio.fixture
async def client(mock_llm):
    app.dependency_overrides[routes.get_llm_client] = lambda: mock_llm
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
