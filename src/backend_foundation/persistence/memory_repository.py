"""Persistence support for minimal continuity memory v0."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from .orm_models import ContinuityMemoryORM


@dataclass(slots=True)
class ContinuityMemoryRecord:
    memory_id: str
    user_id: str
    source_session_id: str
    memory_type: str
    summary_text: str
    confidence: float
    status: str
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None


class SqlAlchemyContinuityMemoryRepository:
    """Stores and recalls lightweight continuity summaries for recent sessions."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, record: ContinuityMemoryRecord) -> None:
        self._db.add(_record_to_orm(record))
        self._db.flush()

    def list_recall_candidates(
        self,
        *,
        user_id: str,
        exclude_session_id: str,
        now: datetime,
        limit: int,
    ) -> list[ContinuityMemoryRecord]:
        stmt = (
            select(ContinuityMemoryORM)
            .where(
                ContinuityMemoryORM.user_id == user_id,
                ContinuityMemoryORM.status == "active",
                ContinuityMemoryORM.source_session_id != exclude_session_id,
                or_(
                    ContinuityMemoryORM.expires_at.is_(None),
                    ContinuityMemoryORM.expires_at > now,
                ),
            )
            .order_by(ContinuityMemoryORM.created_at.desc())
            .limit(limit)
        )
        return [_record_from_orm(item) for item in self._db.scalars(stmt).all()]

    def touch(self, memory_ids: tuple[str, ...], *, used_at: datetime) -> None:
        if not memory_ids:
            return
        stmt = (
            update(ContinuityMemoryORM)
            .where(ContinuityMemoryORM.memory_id.in_(memory_ids))
            .values(last_used_at=used_at)
        )
        self._db.execute(stmt)
        self._db.flush()


def _record_to_orm(record: ContinuityMemoryRecord) -> ContinuityMemoryORM:
    return ContinuityMemoryORM(
        memory_id=record.memory_id,
        user_id=record.user_id,
        source_session_id=record.source_session_id,
        memory_type=record.memory_type,
        summary_text=record.summary_text,
        confidence=record.confidence,
        status=record.status,
        created_at=record.created_at,
        expires_at=record.expires_at,
        last_used_at=record.last_used_at,
    )


def _record_from_orm(orm: ContinuityMemoryORM) -> ContinuityMemoryRecord:
    return ContinuityMemoryRecord(
        memory_id=orm.memory_id,
        user_id=orm.user_id,
        source_session_id=orm.source_session_id,
        memory_type=orm.memory_type,
        summary_text=orm.summary_text,
        confidence=orm.confidence,
        status=orm.status,
        created_at=orm.created_at,
        expires_at=orm.expires_at,
        last_used_at=orm.last_used_at,
    )
