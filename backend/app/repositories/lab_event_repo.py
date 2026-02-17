"""Lab event repository - handles LabEvent and UnmappedRow CRUD operations."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LabEvent, UnmappedRow


class LabEventRepository:
    """Repository for LabEvent operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        biomarker_id: str,
        document_id: str,
        collected_at: datetime,
        value_original: float,
        unit_original: str,
        value_normalized: float,
        unit_canonical: str,
        page: Optional[int] = None,
        panel_name: Optional[str] = None,
        lab_name: Optional[str] = None,
        confidence: float = 1.0,
    ) -> LabEvent:
        """Create a new lab event."""
        event = LabEvent(
            event_id=str(uuid.uuid4()),
            biomarker_id=biomarker_id,
            document_id=document_id,
            collected_at=collected_at,
            value_original=value_original,
            unit_original=unit_original,
            value_normalized=value_normalized,
            unit_canonical=unit_canonical,
            page=page,
            panel_name=panel_name,
            lab_name=lab_name,
            confidence=confidence,
            source_type="pdf_extraction",
        )
        self.db.add(event)
        return event

    def get_by_id(self, event_id: str) -> Optional[LabEvent]:
        """Get lab event by ID."""
        return self.db.get(LabEvent, event_id)

    def get_by_document(
        self, document_id: str, skip: int = 0, limit: int = 100
    ) -> list[LabEvent]:
        """Get all lab events for a document."""
        stmt = (
            select(LabEvent)
            .where(LabEvent.document_id == document_id)
            .offset(skip)
            .limit(limit)
            .order_by(LabEvent.page, LabEvent.created_at)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_biomarker(
        self, biomarker_id: str, skip: int = 0, limit: int = 100
    ) -> list[LabEvent]:
        """Get all lab events for a biomarker (trend data)."""
        stmt = (
            select(LabEvent)
            .where(LabEvent.biomarker_id == biomarker_id)
            .offset(skip)
            .limit(limit)
            .order_by(LabEvent.collected_at)
        )
        return list(self.db.scalars(stmt).all())

    def commit(self) -> None:
        """Commit pending changes."""
        self.db.commit()


class UnmappedRowRepository:
    """Repository for UnmappedRow operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        document_id: str,
        raw_label: str,
        raw_value: Optional[str] = None,
        raw_unit: Optional[str] = None,
        page: Optional[int] = None,
    ) -> UnmappedRow:
        """Create a new unmapped row."""
        row = UnmappedRow(
            row_id=str(uuid.uuid4()),
            document_id=document_id,
            raw_label=raw_label,
            raw_value=raw_value,
            raw_unit=raw_unit,
            page=page,
            status="pending",
        )
        self.db.add(row)
        return row

    def get_by_document(
        self, document_id: str, status: Optional[str] = None
    ) -> list[UnmappedRow]:
        """Get unmapped rows for a document."""
        stmt = select(UnmappedRow).where(UnmappedRow.document_id == document_id)
        if status:
            stmt = stmt.where(UnmappedRow.status == status)
        stmt = stmt.order_by(UnmappedRow.page, UnmappedRow.created_at)
        return list(self.db.scalars(stmt).all())

    def resolve(
        self,
        row_id: str,
        biomarker_id: str,
        notes: Optional[str] = None,
    ) -> Optional[UnmappedRow]:
        """Resolve an unmapped row by assigning it to a biomarker."""
        row = self.db.get(UnmappedRow, row_id)
        if not row:
            return None
        row.status = "resolved"
        row.resolved_biomarker_id = biomarker_id
        row.resolution_notes = notes
        row.resolved_at = datetime.utcnow()
        return row

    def ignore(self, row_id: str, notes: Optional[str] = None) -> Optional[UnmappedRow]:
        """Mark an unmapped row as ignored."""
        row = self.db.get(UnmappedRow, row_id)
        if not row:
            return None
        row.status = "ignored"
        row.resolution_notes = notes
        row.resolved_at = datetime.utcnow()
        return row

    def commit(self) -> None:
        """Commit pending changes."""
        self.db.commit()
