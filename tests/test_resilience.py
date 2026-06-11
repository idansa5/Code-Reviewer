from __future__ import annotations

import datetime as dt

from app.api import routes
from app.config import settings
from app.core.capacity import CapacityLimiter
from app.core.hashing import compute_content_hash
from app.db import repository as repo
from app.db.models import Scan, ScanStatus, utcnow
from app.db.session import async_session_factory
from app.main import app
from app.reviewer import scanner
from tests.helpers import code_for, make_py_file, wait_for_new_tasks


async def test_llm_call_exceeding_timeout_marks_scan_failed(client, mock_llm, monkeypatch):
    monkeypatch.setattr(settings, "llm_timeout_seconds", 0.05)
    mock_llm.delay = 0.2
    before = set(routes._background_tasks)

    submit = await client.post("/scans", files=make_py_file("timeout_case"))
    await wait_for_new_tasks(before)

    result = await client.get(f"/scans/{submit.json()['scan_id']}")
    assert result.json()["status"] == "failed"


async def test_mark_failed_error_still_releases_slot(client, mock_llm, monkeypatch):
    limiter = CapacityLimiter(max_concurrent=1)
    app.dependency_overrides[routes.get_capacity_limiter] = lambda: limiter
    mock_llm.exception = RuntimeError("boom")

    async def broken_mark_failed(session, scan_id, error):
        raise RuntimeError("db write failed")

    monkeypatch.setattr(scanner.repo, "mark_failed", broken_mark_failed)
    before = set(routes._background_tasks)

    await client.post("/scans", files=make_py_file("mark_failed_broken_a"))
    await wait_for_new_tasks(before)

    r2 = await client.post("/scans", files=make_py_file("mark_failed_broken_b"))
    assert r2.status_code == 202


async def test_stale_running_scan_becomes_failed_on_get():
    async with async_session_factory() as session:
        scan = await repo.create_scan(session, "stale-hash-lazy", "stale.py", "x = 1")
        scan.status = ScanStatus.RUNNING.value
        scan.created_at = utcnow() - dt.timedelta(seconds=settings.scan_stale_seconds + 1)
        await session.commit()
        scan_id = scan.id

    async with async_session_factory() as session:
        result = await repo.get_scan(session, scan_id)

    assert result.status == ScanStatus.FAILED.value


async def test_resubmit_does_not_reuse_stale_running_scan(client, mock_llm):
    code = code_for("stale_resubmit")
    content_hash = compute_content_hash(code)

    async with async_session_factory() as session:
        scan = await repo.create_scan(session, content_hash, "stale_resubmit.py", code)
        scan.status = ScanStatus.RUNNING.value
        scan.created_at = utcnow() - dt.timedelta(seconds=settings.scan_stale_seconds + 1)
        await session.commit()
        old_id = scan.id

    before = set(routes._background_tasks)
    submit = await client.post("/scans", files=make_py_file("stale_resubmit"))
    await wait_for_new_tasks(before)

    assert submit.json()["scan_id"] != old_id


async def test_fail_stale_scans_sweep_marks_failed():
    async with async_session_factory() as session:
        scan = await repo.create_scan(session, "stale-hash-sweep", "stale_sweep.py", "x = 1")
        scan.status = ScanStatus.RUNNING.value
        scan.created_at = utcnow() - dt.timedelta(seconds=settings.scan_stale_seconds + 1)
        await session.commit()
        scan_id = scan.id

    async with async_session_factory() as session:
        await repo.fail_stale_scans(session)

    async with async_session_factory() as session:
        scan = await session.get(Scan, scan_id)

    assert scan.status == ScanStatus.FAILED.value
