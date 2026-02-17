from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from app.db.database import Base


class BiomarkerRegistry(Base):
    """
    Authoritative registry of biomarkers.
    Identity comes from here - extraction cannot invent new biomarker_ids.
    """

    __tablename__ = "biomarker_registry"

    biomarker_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    analyte_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specimen: Mapped[str] = mapped_column(String(100), nullable=False)
    measurement_property: Mapped[Optional[str]] = mapped_column(String(100))
    canonical_unit: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    panel_seed: Mapped[Optional[str]] = mapped_column(String(100))
    is_derived: Mapped[bool] = mapped_column(Boolean, default=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    default_reference_range_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    lab_events: Mapped[list["LabEvent"]] = relationship(back_populates="biomarker")

    def __repr__(self) -> str:
        return f"<Biomarker {self.biomarker_id}>"


class Document(Base):
    """
    Uploaded PDF document with metadata.
    """

    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA-256
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Relationships - cascade delete events and unmapped rows when document is deleted
    lab_events: Mapped[list["LabEvent"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    unmapped_rows: Mapped[list["UnmappedRow"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document {self.document_id}: {self.filename}>"


class LabEvent(Base):
    """
    A single biomarker measurement with full provenance.
    Immutable after creation - corrections create new events with supersedes reference.
    """

    __tablename__ = "lab_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    biomarker_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("biomarker_registry.biomarker_id"), nullable=False
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.document_id")
    )

    # Temporal
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Values - preserve original and normalized
    value_original: Mapped[float] = mapped_column(Float, nullable=False)
    unit_original: Mapped[str] = mapped_column(String(50), nullable=False)
    value_normalized: Mapped[float] = mapped_column(Float, nullable=False)
    unit_canonical: Mapped[str] = mapped_column(String(50), nullable=False)

    # Context
    panel_name: Mapped[Optional[str]] = mapped_column(String(100))
    lab_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Provenance
    page: Mapped[Optional[int]] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_type: Mapped[str] = mapped_column(
        String(50), default="pdf_extraction"
    )  # pdf_extraction, manual_entry, import
    
    # Abnormal flag from lab report: 'H' (high), 'L' (low), or null (normal/not specified)
    flag: Mapped[Optional[str]] = mapped_column(String(1))

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    supersedes_event_id: Mapped[Optional[str]] = mapped_column(String(36))

    # Relationships
    biomarker: Mapped["BiomarkerRegistry"] = relationship(back_populates="lab_events")
    document: Mapped[Optional["Document"]] = relationship(back_populates="lab_events")

    __table_args__ = (
        Index("ix_lab_events_biomarker_collected", "biomarker_id", "collected_at"),
        Index("ix_lab_events_document", "document_id"),
    )

    def __repr__(self) -> str:
        return f"<LabEvent {self.event_id}: {self.biomarker_id} @ {self.collected_at}>"


class UnmappedRow(Base):
    """
    Rows extracted from PDFs that couldn't be mapped to the registry.
    Surfaced for human review - never silently dropped.
    """

    __tablename__ = "unmapped_rows"

    row_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.document_id"), nullable=False
    )

    # Raw extracted data
    raw_label: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[Optional[str]] = mapped_column(Text)
    raw_unit: Mapped[Optional[str]] = mapped_column(String(50))
    page: Mapped[Optional[int]] = mapped_column(Integer)

    # Resolution status
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, resolved, ignored
    resolved_biomarker_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("biomarker_registry.biomarker_id")
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="unmapped_rows")

    __table_args__ = (Index("ix_unmapped_rows_status", "status"),)

    def __repr__(self) -> str:
        return f"<UnmappedRow {self.row_id}: {self.raw_label}>"
