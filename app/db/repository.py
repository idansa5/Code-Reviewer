from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import RuleResult, Scan, ScanStatus, utcnow


REUSABLE_STATUSES = (
    ScanStatus.PENDING.value,
    ScanStatus.RUNNING.value,
    ScanStatus.COMPLETED.value,
)


def _cutoff(ttl_hours: int | None) -> dt.datetime:
    hours = settings.result_ttl_hours if ttl_hours is None else ttl_hours
    return utcnow() - dt.timedelta(hours=hours)


def _stale_cutoff() -> dt.datetime:
    return utcnow() - dt.timedelta(seconds=settings.scan_stale_seconds)


async def find_reusable_scan(
    session: AsyncSession, content_hash: str, ttl_hours: int | None = None
) -> Scan | None:
    stmt = (
        select(Scan)
        .where(
            Scan.content_hash == content_hash,
            Scan.status.in_(REUSABLE_STATUSES),
            Scan.created_at >= _cutoff(ttl_hours),
        )
        .order_by(Scan.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_scan(
    session: AsyncSession, content_hash: str, filename: str, code: str
) -> Scan:
    scan = Scan(
        content_hash=content_hash,
        filename=filename,
        code=code,
        status=ScanStatus.PENDING.value,
    )
    session.add(scan)
    await session.commit()
    await session.refresh(scan)
    return scan


async def mark_running(session: AsyncSession, scan_id: str) -> None:
    scan = await session.get(Scan, scan_id)
    scan.status = ScanStatus.RUNNING.value
    await session.commit()


async def save_rule_result(
    session: AsyncSession,
    scan_id: str,
    rule_id: str,
    rule_name: str,
    adheres: bool | None,
    detail: str | None,
) -> None:
    session.add(
        RuleResult(
            scan_id=scan_id,
            rule_id=rule_id,
            rule_name=rule_name,
            adheres=adheres,
            detail=detail,
        )
    )
    await session.commit()


async def mark_completed(session: AsyncSession, scan_id: str) -> None:
    scan = await session.get(Scan, scan_id)
    scan.status = ScanStatus.COMPLETED.value
    scan.completed_at = utcnow()
    await session.commit()


async def mark_failed(session: AsyncSession, scan_id: str, error: str) -> None:
    scan = await session.get(Scan, scan_id)
    scan.status = ScanStatus.FAILED.value
    scan.completed_at = utcnow()
    scan.error = error
    await session.commit()


async def get_scan(
    session: AsyncSession, scan_id: str, ttl_hours: int | None = None
) -> Scan | None:
    stmt = (
        select(Scan)
        .where(Scan.id == scan_id, Scan.created_at >= _cutoff(ttl_hours))
        .options(selectinload(Scan.results))
    )
    result = await session.execute(stmt)
    scan = result.scalar_one_or_none()  # for stict max one row
    # Lazy fixup: check if the worker died mid-scan. Otherwise the row would stay

    if (
        scan is not None
        and scan.status == ScanStatus.RUNNING.value
        and scan.created_at < _stale_cutoff()
    ):
        scan.status = ScanStatus.FAILED.value
        scan.completed_at = utcnow()
        scan.error = "Scan timed out"
        await session.commit()
    return scan


# turn to failed  scans that got "hanged"
async def fail_stale_scans(session: AsyncSession) -> int:
    stmt = (
        update(Scan)
        .where(
            Scan.status == ScanStatus.RUNNING.value, Scan.created_at < _stale_cutoff()
        )
        .values(
            status=ScanStatus.FAILED.value,
            completed_at=utcnow(),
            error="Scan timed out",
        )
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0


async def delete_expired_scans(
    session: AsyncSession, ttl_hours: int | None = None
) -> int:
    stmt = delete(Scan).where(Scan.created_at < _cutoff(ttl_hours))
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0
