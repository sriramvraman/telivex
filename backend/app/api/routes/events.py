"""LabEvent API routes - CRUD operations for lab events."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BiomarkerRegistry
from app.repositories.lab_event_repo import LabEventRepository
from app.schemas.document import LabEventResponse

router = APIRouter(prefix="/events", tags=["events"])


class LabEventCreate(BaseModel):
    """Request schema for creating a manual lab event."""

    biomarker_id: str = Field(..., description="Registry biomarker ID")
    collected_at: datetime = Field(..., description="When the sample was collected")
    value: float = Field(..., description="Measured value")
    unit: str = Field(..., description="Unit of measurement")
    lab_name: Optional[str] = Field(None, description="Lab name")
    panel_name: Optional[str] = Field(
        None, description="Panel name (e.g., Lipid Profile)"
    )


class LabEventUpdate(BaseModel):
    """Request schema for correcting a lab event (creates superseding event)."""

    value: Optional[float] = Field(None, description="Corrected value")
    unit: Optional[str] = Field(None, description="Corrected unit")
    collected_at: Optional[datetime] = Field(None, description="Corrected date")
    correction_reason: Optional[str] = Field(
        None, description="Why the correction was made"
    )


class LabEventDetailResponse(LabEventResponse):
    """Extended lab event response with provenance details."""

    document_id: Optional[str] = None
    lab_name: Optional[str] = None
    panel_name: Optional[str] = None
    source_type: str = "manual_entry"
    supersedes_event_id: Optional[str] = None
    created_at: datetime


@router.get("", response_model=list[LabEventDetailResponse])
def list_events(
    biomarker_id: Optional[str] = Query(None, description="Filter by biomarker"),
    start_date: Optional[datetime] = Query(None, description="From date"),
    end_date: Optional[datetime] = Query(None, description="Until date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    List lab events with optional filtering.

    Supports filtering by biomarker ID and date range.
    """
    event_repo = LabEventRepository(db)
    events = event_repo.list_events(
        biomarker_id=biomarker_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )

    return [
        LabEventDetailResponse(
            event_id=event.event_id,
            biomarker_id=event.biomarker_id,
            analyte_name=event.biomarker.analyte_name,
            collected_at=event.collected_at,
            value_normalized=event.value_normalized,
            unit_canonical=event.unit_canonical,
            value_original=event.value_original,
            unit_original=event.unit_original,
            page=event.page,
            confidence=event.confidence,
            document_id=event.document_id,
            lab_name=event.lab_name,
            panel_name=event.panel_name,
            source_type=event.source_type,
            supersedes_event_id=event.supersedes_event_id,
            created_at=event.created_at,
        )
        for event in events
    ]


@router.get("/{event_id}", response_model=LabEventDetailResponse)
def get_event(event_id: str, db: Session = Depends(get_db)):
    """Get a specific lab event by ID."""
    event_repo = LabEventRepository(db)
    event = event_repo.get_by_id(event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Lab event not found")

    return LabEventDetailResponse(
        event_id=event.event_id,
        biomarker_id=event.biomarker_id,
        analyte_name=event.biomarker.analyte_name,
        collected_at=event.collected_at,
        value_normalized=event.value_normalized,
        unit_canonical=event.unit_canonical,
        value_original=event.value_original,
        unit_original=event.unit_original,
        page=event.page,
        confidence=event.confidence,
        document_id=event.document_id,
        lab_name=event.lab_name,
        panel_name=event.panel_name,
        source_type=event.source_type,
        supersedes_event_id=event.supersedes_event_id,
        created_at=event.created_at,
    )


@router.post("", response_model=LabEventDetailResponse, status_code=201)
def create_event(
    event_data: LabEventCreate,
    db: Session = Depends(get_db),
):
    """
    Create a manual lab event (not from PDF extraction).

    The value is stored in both original and normalized form.
    Unit conversion is not applied for manual entries - user provides
    the value in canonical units directly.
    """
    # Verify biomarker exists
    biomarker = db.get(BiomarkerRegistry, event_data.biomarker_id)
    if not biomarker:
        raise HTTPException(
            status_code=400,
            detail=f"Biomarker '{event_data.biomarker_id}' not found in registry",
        )

    event_repo = LabEventRepository(db)
    event = event_repo.create_manual(
        biomarker_id=event_data.biomarker_id,
        collected_at=event_data.collected_at,
        value=event_data.value,
        unit=event_data.unit,
        lab_name=event_data.lab_name,
        panel_name=event_data.panel_name,
    )
    event_repo.commit()

    # Refresh to get relationship data
    db.refresh(event)

    return LabEventDetailResponse(
        event_id=event.event_id,
        biomarker_id=event.biomarker_id,
        analyte_name=event.biomarker.analyte_name,
        collected_at=event.collected_at,
        value_normalized=event.value_normalized,
        unit_canonical=event.unit_canonical,
        value_original=event.value_original,
        unit_original=event.unit_original,
        page=event.page,
        confidence=event.confidence,
        document_id=event.document_id,
        lab_name=event.lab_name,
        panel_name=event.panel_name,
        source_type=event.source_type,
        supersedes_event_id=event.supersedes_event_id,
        created_at=event.created_at,
    )


@router.post(
    "/{event_id}/correct", response_model=LabEventDetailResponse, status_code=201
)
def correct_event(
    event_id: str,
    correction: LabEventUpdate,
    db: Session = Depends(get_db),
):
    """
    Create a correction for an existing lab event.

    Following the append-only model, this creates a NEW event that
    supersedes the original. The original event is preserved for audit.
    """
    event_repo = LabEventRepository(db)
    original = event_repo.get_by_id(event_id)

    if not original:
        raise HTTPException(status_code=404, detail="Lab event not found")

    # Create corrected event
    new_event = event_repo.create_correction(
        original_event=original,
        value=correction.value,
        unit=correction.unit,
        collected_at=correction.collected_at,
        reason=correction.correction_reason,
    )
    event_repo.commit()

    # Refresh to get relationship data
    db.refresh(new_event)

    return LabEventDetailResponse(
        event_id=new_event.event_id,
        biomarker_id=new_event.biomarker_id,
        analyte_name=new_event.biomarker.analyte_name,
        collected_at=new_event.collected_at,
        value_normalized=new_event.value_normalized,
        unit_canonical=new_event.unit_canonical,
        value_original=new_event.value_original,
        unit_original=new_event.unit_original,
        page=new_event.page,
        confidence=new_event.confidence,
        document_id=new_event.document_id,
        lab_name=new_event.lab_name,
        panel_name=new_event.panel_name,
        source_type=new_event.source_type,
        supersedes_event_id=new_event.supersedes_event_id,
        created_at=new_event.created_at,
    )


@router.get("/{event_id}/history", response_model=list[LabEventDetailResponse])
def get_event_history(event_id: str, db: Session = Depends(get_db)):
    """
    Get the correction history for an event.

    Returns the chain of events: original → corrections.
    """
    event_repo = LabEventRepository(db)
    original = event_repo.get_by_id(event_id)

    if not original:
        raise HTTPException(status_code=404, detail="Lab event not found")

    history = event_repo.get_history(event_id)

    return [
        LabEventDetailResponse(
            event_id=event.event_id,
            biomarker_id=event.biomarker_id,
            analyte_name=event.biomarker.analyte_name,
            collected_at=event.collected_at,
            value_normalized=event.value_normalized,
            unit_canonical=event.unit_canonical,
            value_original=event.value_original,
            unit_original=event.unit_original,
            page=event.page,
            confidence=event.confidence,
            document_id=event.document_id,
            lab_name=event.lab_name,
            panel_name=event.panel_name,
            source_type=event.source_type,
            supersedes_event_id=event.supersedes_event_id,
            created_at=event.created_at,
        )
        for event in history
    ]
