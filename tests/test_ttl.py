from __future__ import annotations

import datetime as dt

from app.db import repository as repo
from app.db.models import Scan, utcnow
from app.db.session import async_session_factory


async def test_expired_scan_returns_none_before_cleanup():
    async with async_session_factory() as session:
        scan = await repo.create_scan(session, "ttl-hash-lazy", "ttl.py", "x = 1")
        scan.created_at = utcnow() - dt.timedelta(hours=25)
        await session.commit()
        scan_id = scan.id

    async with async_session_factory() as session:
        result = await repo.get_scan(session, scan_id)

    assert result is None


async def test_cleanup_deletes_expired_scan():
    async with async_session_factory() as session:
        scan = await repo.create_scan(session, "ttl-hash-cleanup", "ttl2.py", "x = 1")
        scan.created_at = utcnow() - dt.timedelta(hours=25)
        await session.commit()
        scan_id = scan.id

    async with async_session_factory() as session:
        await repo.delete_expired_scans(session)

    async with async_session_factory() as session:
        assert await session.get(Scan, scan_id) is None
