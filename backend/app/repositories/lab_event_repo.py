"""Lab event repository - handles LabEvent and UnmappedRow CRUD operations."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
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
        flag: Optional[str] = None,
    ) -> LabEvent:
        """Create a new lab event from PDF extraction."""
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
            flag=flag,
        )
        self.db.add(event)
        return event

    def create_manual(
        self,
        biomarker_id: str,
        collected_at: datetime,
        value: float,
        unit: str,
        lab_name: Optional[str] = None,
        panel_name: Optional[str] = None,
    ) -> LabEvent:
        """Create a manual lab event entry (not from PDF)."""
        event = LabEvent(
            event_id=str(uuid.uuid4()),
            biomarker_id=biomarker_id,
            document_id=None,
            collected_at=collected_at,
            value_original=value,
            unit_original=unit,
            value_normalized=value,  # Manual entries assumed to be in canonical unit
            unit_canonical=unit,
            page=None,
            panel_name=panel_name,
            lab_name=lab_name,
            confidence=1.0,
            source_type="manual_entry",
        )
        self.db.add(event)
        return event

    def create_correction(
        self,
        original_event: LabEvent,
        value: Optional[float] = None,
        unit: Optional[str] = None,
        collected_at: Optional[datetime] = None,
        reason: Optional[str] = None,
    ) -> LabEvent:
        """Create a correction event that supersedes an existing event."""
        corrected = LabEvent(
            event_id=str(uuid.uuid4()),
            biomarker_id=original_event.biomarker_id,
            document_id=original_event.document_id,
            collected_at=collected_at or original_event.collected_at,
            value_original=value
            if value is not None
            else original_event.value_original,
            unit_original=unit or original_event.unit_original,
            value_normalized=value
            if value is not None
            else original_event.value_normalized,
            unit_canonical=unit or original_event.unit_canonical,
            page=original_event.page,
            panel_name=original_event.panel_name,
            lab_name=original_event.lab_name,
            confidence=1.0,  # Manual corrections are high confidence
            source_type="correction",
            supersedes_event_id=original_event.event_id,
        )
        self.db.add(corrected)
        return corrected

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

    def get_trend(
        self,
        biomarker_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 500,
    ) -> list[LabEvent]:
        """Get trend data (time series) for a biomarker with date filtering."""
        stmt = select(LabEvent).where(LabEvent.biomarker_id == biomarker_id)

        if start_date:
            stmt = stmt.where(LabEvent.collected_at >= start_date)
        if end_date:
            stmt = stmt.where(LabEvent.collected_at <= end_date)

        stmt = stmt.order_by(LabEvent.collected_at).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_summary(self, biomarker_id: str) -> dict:
        """Get summary statistics for a biomarker."""
        stmt = select(
            func.count(LabEvent.event_id).label("event_count"),
            func.min(LabEvent.value_normalized).label("min_value"),
            func.max(LabEvent.value_normalized).label("max_value"),
            func.avg(LabEvent.value_normalized).label("avg_value"),
            func.min(LabEvent.collected_at).label("first_date"),
            func.max(LabEvent.collected_at).label("last_date"),
        ).where(LabEvent.biomarker_id == biomarker_id)

        result = self.db.execute(stmt).first()

        if not result or result.event_count == 0:
            return {
                "event_count": 0,
                "min_value": None,
                "max_value": None,
                "avg_value": None,
                "first_date": None,
                "last_date": None,
                "latest_value": None,
            }

        # Get latest value
        latest_stmt = (
            select(LabEvent.value_normalized)
            .where(LabEvent.biomarker_id == biomarker_id)
            .order_by(LabEvent.collected_at.desc())
            .limit(1)
        )
        latest = self.db.scalar(latest_stmt)

        return {
            "event_count": result.event_count,
            "min_value": result.min_value,
            "max_value": result.max_value,
            "avg_value": round(result.avg_value, 2) if result.avg_value else None,
            "first_date": result.first_date,
            "last_date": result.last_date,
            "latest_value": latest,
        }

    def list_events(
        self,
        biomarker_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LabEvent]:
        """List events with optional filtering."""
        stmt = select(LabEvent)

        if biomarker_id:
            stmt = stmt.where(LabEvent.biomarker_id == biomarker_id)
        if start_date:
            stmt = stmt.where(LabEvent.collected_at >= start_date)
        if end_date:
            stmt = stmt.where(LabEvent.collected_at <= end_date)

        stmt = stmt.order_by(LabEvent.collected_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_history(self, event_id: str) -> list[LabEvent]:
        """Get the correction history chain for an event."""
        history = []
        current_id = event_id

        # Walk backwards to find original
        while current_id:
            event = self.get_by_id(current_id)
            if not event:
                break
            history.insert(0, event)
            # Find if this event supersedes another
            # Walk back through supersedes chain
            stmt = select(LabEvent).where(
                LabEvent.event_id == event.supersedes_event_id
            )
            predecessor = self.db.scalar(stmt)
            if predecessor:
                current_id = predecessor.event_id
                if current_id not in [e.event_id for e in history]:
                    history.insert(0, predecessor)
            current_id = None

        # Now find all corrections that supersede this event
        original_id = history[0].event_id if history else event_id
        corrections = self._find_corrections(original_id, history)
        history.extend(corrections)

        return history

    def _find_corrections(
        self, event_id: str, already_found: list[LabEvent]
    ) -> list[LabEvent]:
        """Find all events that supersede the given event."""
        found_ids = {e.event_id for e in already_found}
        corrections = []

        stmt = select(LabEvent).where(LabEvent.supersedes_event_id == event_id)
        results = list(self.db.scalars(stmt).all())

        for correction in results:
            if correction.event_id not in found_ids:
                corrections.append(correction)
                found_ids.add(correction.event_id)
                # Recursively find corrections of corrections
                nested = self._find_corrections(
                    correction.event_id, already_found + corrections
                )
                corrections.extend(nested)

        return corrections

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
