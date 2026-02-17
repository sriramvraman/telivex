"""Trend API routes - time series queries for biomarkers."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BiomarkerRegistry
from app.repositories.lab_event_repo import LabEventRepository
from app.services.canonicalizer import get_category_for_panel

router = APIRouter(prefix="/biomarkers", tags=["trends"])


class TrendPoint(BaseModel):
    """A single point in a biomarker trend."""

    event_id: str
    collected_at: datetime
    value_normalized: float
    unit_canonical: str
    value_original: float
    unit_original: str
    document_id: Optional[str]
    page: Optional[int]
    lab_name: Optional[str]
    confidence: float

    model_config = {"from_attributes": True}


class TrendResponse(BaseModel):
    """Trend response with metadata and time series."""

    biomarker_id: str
    analyte_name: str
    canonical_unit: str
    category: Optional[str]
    total_points: int
    points: list[TrendPoint]


@router.get("/{biomarker_id}/trend", response_model=TrendResponse)
def get_biomarker_trend(
    biomarker_id: str,
    start_date: Optional[datetime] = Query(
        None, description="Filter events from this date"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter events until this date"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get trend data (time series) for a specific biomarker.

    Returns all LabEvents for this biomarker ordered by collection date.
    Each point includes provenance (document_id, page) so the user can
    drill down to the source PDF.
    """
    # Verify biomarker exists
    biomarker = db.get(BiomarkerRegistry, biomarker_id)
    if not biomarker:
        raise HTTPException(status_code=404, detail="Biomarker not found")

    event_repo = LabEventRepository(db)

    # Get events with optional date filtering
    events = event_repo.get_trend(
        biomarker_id=biomarker_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )

    # Build trend points
    points = [
        TrendPoint(
            event_id=event.event_id,
            collected_at=event.collected_at,
            value_normalized=event.value_normalized,
            unit_canonical=event.unit_canonical,
            value_original=event.value_original,
            unit_original=event.unit_original,
            document_id=event.document_id,
            page=event.page,
            lab_name=event.lab_name,
            confidence=event.confidence,
        )
        for event in events
    ]

    return TrendResponse(
        biomarker_id=biomarker.biomarker_id,
        analyte_name=biomarker.analyte_name,
        canonical_unit=biomarker.canonical_unit,
        category=get_category_for_panel(biomarker.panel_seed),
        total_points=len(points),
        points=points,
    )


@router.get("/{biomarker_id}/summary")
def get_biomarker_summary(
    biomarker_id: str,
    db: Session = Depends(get_db),
):
    """
    Get summary statistics for a biomarker.

    Returns min, max, latest value, and event count.
    """
    # Verify biomarker exists
    biomarker = db.get(BiomarkerRegistry, biomarker_id)
    if not biomarker:
        raise HTTPException(status_code=404, detail="Biomarker not found")

    event_repo = LabEventRepository(db)
    stats = event_repo.get_summary(biomarker_id)

    return {
        "biomarker_id": biomarker.biomarker_id,
        "analyte_name": biomarker.analyte_name,
        "canonical_unit": biomarker.canonical_unit,
        **stats,
    }
