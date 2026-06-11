from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.api import routes
from app.config import settings
from app.core.hashing import compute_content_hash
from app.db.models import Scan
from app.db.session import async_session_factory
from tests.helpers import code_for, make_py_file, wait_for_new_tasks


async def test_identical_content_is_cached_without_rerunning_llm(client, mock_llm):
    before = set(routes._background_tasks)
    await client.post("/scans", files=make_py_file("cache_hit"))
    await wait_for_new_tasks(before)
    calls_after_first = len(mock_llm.calls)

    await client.post("/scans", files=make_py_file("cache_hit"))

    assert len(mock_llm.calls) == calls_after_first


async def test_cache_miss_when_model_changes(client, mock_llm, monkeypatch):
    before = set(routes._background_tasks)
    r1 = await client.post("/scans", files=make_py_file("cache_model"))
    await wait_for_new_tasks(before)

    monkeypatch.setattr(settings, "ollama_model", "a-different-model")
    before2 = set(routes._background_tasks)
    r2 = await client.post("/scans", files=make_py_file("cache_model"))
    await wait_for_new_tasks(before2)

    assert r2.json()["scan_id"] != r1.json()["scan_id"]


async def test_concurrent_identical_posts_create_single_scan_row(client, mock_llm):
    before = set(routes._background_tasks)
    await asyncio.gather(
        client.post("/scans", files=make_py_file("cache_dedup")),
        client.post("/scans", files=make_py_file("cache_dedup")),
    )
    await wait_for_new_tasks(before)

    content_hash = compute_content_hash(code_for("cache_dedup"))
    async with async_session_factory() as session:
        rows = (await session.execute(select(Scan).where(Scan.content_hash == content_hash))).scalars().all()

    assert len(rows) == 1


async def test_failed_scan_is_not_reused(client, mock_llm):
    mock_llm.exception = RuntimeError("boom")
    before = set(routes._background_tasks)
    r1 = await client.post("/scans", files=make_py_file("cache_failed"))
    await wait_for_new_tasks(before)

    mock_llm.exception = None
    before2 = set(routes._background_tasks)
    r2 = await client.post("/scans", files=make_py_file("cache_failed"))
    await wait_for_new_tasks(before2)

    assert r2.json()["scan_id"] != r1.json()["scan_id"]
