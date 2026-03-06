from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import cast, func, String
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BiomarkerRegistry
from app.schemas.biomarker import BiomarkerResponse, BiomarkerListResponse
from app.services.canonicalizer import _load_panel_category_map

router = APIRouter(prefix="/biomarkers", tags=["biomarkers"])


@router.get("", response_model=BiomarkerListResponse)
def list_biomarkers(
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search in name or aliases"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List all biomarkers with optional filtering."""
    query = db.query(BiomarkerRegistry)

    if category:
        query = query.filter(BiomarkerRegistry.category == category)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            BiomarkerRegistry.analyte_name.ilike(search_pattern)
            | BiomarkerRegistry.aliases.any(search)
        )

    total = query.count()
    biomarkers = query.offset(skip).limit(limit).all()

    return BiomarkerListResponse(biomarkers=biomarkers, total=total)


@router.get("/categories")
def list_categories():
    """List all unique biomarker categories from the panel_seed → category mapping."""
    mapping = _load_panel_category_map()
    categories = sorted(set(mapping.values()))
    return {"categories": categories}


@router.get("/search", response_model=list[BiomarkerResponse])
def search_biomarkers(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search biomarkers by name, alias, LOINC component, or panel seed."""
    pattern = f"%{q}%"
    # Cast the ARRAY column to text for ilike matching across all aliases
    aliases_text = cast(BiomarkerRegistry.aliases, String)
    results = (
        db.query(BiomarkerRegistry)
        .filter(
            BiomarkerRegistry.analyte_name.ilike(pattern)
            | BiomarkerRegistry.biomarker_id.ilike(pattern)
            | aliases_text.ilike(pattern)
            | BiomarkerRegistry.panel_seed.ilike(pattern)
            | func.coalesce(BiomarkerRegistry.loinc_component, "").ilike(pattern)
        )
        .limit(limit)
        .all()
    )
    return results


@router.get("/{biomarker_id}", response_model=BiomarkerResponse)
def get_biomarker(biomarker_id: str, db: Session = Depends(get_db)):
    """Get a specific biomarker by ID."""
    biomarker = (
        db.query(BiomarkerRegistry)
        .filter(BiomarkerRegistry.biomarker_id == biomarker_id)
        .first()
    )
    if not biomarker:
        raise HTTPException(status_code=404, detail="Biomarker not found")
    return biomarker
