"""Trend API routes - time series queries for biomarkers."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BiomarkerRegistry, LabEvent
from app.repositories.lab_event_repo import LabEventRepository
from app.services.canonicalizer import get_category_for_panel

router = APIRouter(prefix="/trends", tags=["trends"])


class TrendPoint(BaseModel):
    """A single point in a biomarker trend."""

    event_id: str
    collected_at: datetime
    value: float  # Use simple 'value' for frontend compatibility
    unit: str     # Use simple 'unit' for frontend compatibility
    value_original: float
    unit_original: str
    document_id: Optional[str]
    page: Optional[int]
    lab_name: Optional[str]
    confidence: float
    flag: Optional[str] = None  # H=high, L=low, null=normal

    model_config = {"from_attributes": True}


class TrendResponse(BaseModel):
    """Trend response with metadata and time series."""

    biomarker_id: str
    analyte_name: str
    canonical_unit: str
    category: Optional[str]
    reference_range: Optional[str] = None
    total_points: int
    points: list[TrendPoint]


class AvailableTrend(BaseModel):
    """A biomarker with available trend data."""

    biomarker_id: str
    biomarker_name: str
    canonical_unit: str
    category: Optional[str]
    event_count: int
    latest_value: Optional[float]
    latest_date: Optional[datetime]


@router.get("", response_model=list[AvailableTrend])
def list_available_trends(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
):
    """
    List all biomarkers that have trend data available.
    
    Returns biomarkers with at least one lab event, sorted by event count.
    Use this to populate the trend selector UI.
    """
    # Get biomarkers with event counts
    stmt = (
        select(
            LabEvent.biomarker_id,
            func.count(LabEvent.event_id).label("event_count"),
            func.max(LabEvent.collected_at).label("latest_date"),
        )
        .group_by(LabEvent.biomarker_id)
        .order_by(func.count(LabEvent.event_id).desc())
    )
    
    results = db.execute(stmt).all()
    
    available_trends = []
    for row in results:
        biomarker = db.get(BiomarkerRegistry, row.biomarker_id)
        if not biomarker:
            continue
        
        # Get category from panel_seed mapping
        cat = get_category_for_panel(biomarker.panel_seed)
        
        # Apply category filter if specified
        if category and cat != category:
            continue
        
        # Get latest value
        latest_stmt = (
            select(LabEvent.value_normalized)
            .where(LabEvent.biomarker_id == row.biomarker_id)
            .order_by(LabEvent.collected_at.desc())
            .limit(1)
        )
        latest_value = db.scalar(latest_stmt)
        
        available_trends.append(
            AvailableTrend(
                biomarker_id=biomarker.biomarker_id,
                biomarker_name=biomarker.analyte_name,
                canonical_unit=biomarker.canonical_unit,
                category=cat,
                event_count=row.event_count,
                latest_value=latest_value,
                latest_date=row.latest_date,
            )
        )
    
    return available_trends


@router.get("/{biomarker_id}", response_model=TrendResponse)
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
            value=event.value_normalized,
            unit=event.unit_canonical,
            value_original=event.value_original,
            unit_original=event.unit_original,
            document_id=event.document_id,
            page=event.page,
            lab_name=event.lab_name,
            confidence=event.confidence,
            flag=event.flag,
        )
        for event in events
    ]

    return TrendResponse(
        biomarker_id=biomarker.biomarker_id,
        analyte_name=biomarker.analyte_name,
        canonical_unit=biomarker.canonical_unit,
        category=get_category_for_panel(biomarker.panel_seed),
        reference_range=biomarker.default_reference_range_notes,
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

    Returns min, max, avg, latest value, and event count.
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
        "category": get_category_for_panel(biomarker.panel_seed),
        "reference_range": biomarker.default_reference_range_notes,
        **stats,
    }


@router.get("/categories/list")
def list_categories(db: Session = Depends(get_db)):
    """
    List all categories that have trend data.
    
    Useful for filtering the trend list by category.
    """
    # Get distinct categories from biomarkers with events
    stmt = (
        select(LabEvent.biomarker_id)
        .distinct()
    )
    biomarker_ids = [row for row in db.scalars(stmt)]
    
    categories = set()
    for bid in biomarker_ids:
        biomarker = db.get(BiomarkerRegistry, bid)
        if biomarker:
            cat = get_category_for_panel(biomarker.panel_seed)
            if cat:
                categories.add(cat)
    
    return sorted(list(categories))
