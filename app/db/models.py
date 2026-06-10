from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import ForeignKey, Index, String, Text, DateTime, Boolean, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (
        Index("ix_scans_content_hash_status_created_at", "content_hash", "status", "created_at"),
        Index("ix_scans_created_at", "created_at"),
        # Defensive backstop against duplicate concurrent scans of the same content
        # (primary guard is an asyncio.Lock around the cache lookup + insert).
        Index(
            "uq_scans_content_hash_inflight",
            "content_hash",
            unique=True,
            sqlite_where=text("status IN ('pending', 'running')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ScanStatus.PENDING.value)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)

    results: Mapped[list[RuleResult]] = relationship(
        back_populates="scan", cascade="all, delete-orphan"
    )


class RuleResult(Base):
    __tablename__ = "rule_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    adheres: Mapped[bool | None] = mapped_column(Boolean)
    detail: Mapped[str | None] = mapped_column(Text)

    scan: Mapped[Scan] = relationship(back_populates="results")
