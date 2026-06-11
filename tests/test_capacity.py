from __future__ import annotations

import asyncio

from app.api import routes
from app.core.capacity import CapacityLimiter
from app.main import app
from tests.helpers import make_py_file, wait_for_new_tasks


async def test_capacity_returns_503_when_full(client, mock_llm):
    limiter = CapacityLimiter(max_concurrent=2)
    app.dependency_overrides[routes.get_capacity_limiter] = lambda: limiter
    mock_llm.block_event = asyncio.Event()
    before = set(routes._background_tasks)
    try:
        await client.post("/scans", files=make_py_file("cap_full_a"))
        await client.post("/scans", files=make_py_file("cap_full_b"))
        r3 = await client.post("/scans", files=make_py_file("cap_full_c"))

        assert r3.status_code == 503
    finally:
        mock_llm.block_event.set()
        await wait_for_new_tasks(before)


async def test_slot_freed_after_scan_completes(client, mock_llm):
    limiter = CapacityLimiter(max_concurrent=1)
    app.dependency_overrides[routes.get_capacity_limiter] = lambda: limiter
    before = set(routes._background_tasks)

    r1 = await client.post("/scans", files=make_py_file("slot_freed_a"))
    await wait_for_new_tasks(before)

    r2 = await client.post("/scans", files=make_py_file("slot_freed_b"))

    assert r1.status_code == 202 and r2.status_code == 202


async def test_failed_scan_marks_status_failed(client, mock_llm):
    mock_llm.exception = RuntimeError("boom")
    before = set(routes._background_tasks)
    submit = await client.post("/scans", files=make_py_file("fail_status"))
    await wait_for_new_tasks(before)

    result = await client.get(f"/scans/{submit.json()['scan_id']}")
    assert result.json()["status"] == "failed"


async def test_failed_scan_releases_capacity_slot(client, mock_llm):
    limiter = CapacityLimiter(max_concurrent=1)
    app.dependency_overrides[routes.get_capacity_limiter] = lambda: limiter
    mock_llm.exception = RuntimeError("boom")
    before = set(routes._background_tasks)

    await client.post("/scans", files=make_py_file("fail_slot_a"))
    await wait_for_new_tasks(before)

    r2 = await client.post("/scans", files=make_py_file("fail_slot_b"))
    assert r2.status_code == 202
