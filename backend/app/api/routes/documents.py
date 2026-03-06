"""Document API routes - upload, extraction, and retrieval."""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.db.database import get_db
from app.db.models import User
from app.repositories.document_repo import DocumentRepository
from app.repositories.lab_event_repo import LabEventRepository, UnmappedRowRepository
from app.schemas.document import (
    DocumentResponse,
    DocumentUploadResponse,
    LabEventResponse,
    UnmappedRowResponse,
)
from app.services.canonicalizer import Canonicalizer, get_category_for_panel
from app.services.extractor import PDFExtractor
from app.services.normalizer import UnitNormalizer

router = APIRouter(prefix="/documents", tags=["documents"])

# Storage configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    lab_name: Optional[str] = Query(None, description="Lab name if not in PDF"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Upload a lab report PDF and extract biomarker data.

    The PDF is processed to extract lab values which are then:
    1. Canonicalized against the BiomarkerRegistry
    2. Normalized to canonical units
    3. Stored as LabEvents with full provenance

    Dates are extracted from the PDF:
    - collected_at: when the sample was collected
    - reported_at: when the lab report was generated
    - uploaded_at: when the document was uploaded (auto-set)

    Rows that cannot be matched are stored as UnmappedRows for review.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save the uploaded file
    file_path = (
        UPLOAD_DIR / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    )
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Calculate file hash
    file_hash = get_file_hash(file_path)

    # Extract data from PDF
    extractor = PDFExtractor()
    extraction_result = extractor.extract(file_path)

    if extraction_result.errors:
        # Log errors but continue processing
        pass

    # Parse dates extracted from PDF (both may be None)
    collected_at: Optional[datetime] = None
    reported_at: Optional[datetime] = None

    if extraction_result.collected_date:
        try:
            collected_at = datetime.strptime(
                extraction_result.collected_date, "%Y-%m-%d"
            )
        except ValueError:
            pass

    if extraction_result.reported_date:
        try:
            reported_at = datetime.strptime(extraction_result.reported_date, "%Y-%m-%d")
        except ValueError:
            pass

    # Create document record with extracted dates
    doc_repo = DocumentRepository(db)
    document = doc_repo.create(
        filename=file.filename,
        storage_path=str(file_path),
        page_count=extraction_result.page_count,
        file_hash=file_hash,
        collected_at=collected_at,
        reported_at=reported_at,
        user_id=current_user.user_id if current_user else None,
    )

    # Initialize services
    canonicalizer = Canonicalizer(db)
    normalizer = UnitNormalizer()
    event_repo = LabEventRepository(db)
    unmapped_repo = UnmappedRowRepository(db)

    # LabEvent collected_at: prefer collected_at, fall back to reported_at, then uploaded_at
    event_date = collected_at or reported_at or document.uploaded_at

    events_created = 0
    unmapped_count = 0
    # Track (biomarker_id, value_normalized) to deduplicate repeated values
    # within the same document (e.g., Creatinine repeated on eGFR page)
    seen_events: set[tuple[str, float]] = set()

    # Process each extracted row
    for row in extraction_result.rows:
        # Try to canonicalize the label (with section context for disambiguation)
        canon_result = canonicalizer.canonicalize(row.label, section=row.section)

        if not canon_result.matched:
            unmapped_repo.create(
                document_id=document.document_id,
                raw_label=row.label,
                raw_value=row.value,
                raw_unit=row.unit,
                page=row.page,
            )
            unmapped_count += 1
            continue

        # Matched - normalize the unit
        assert canon_result.match is not None
        try:
            norm_result = normalizer.normalize(
                value=row.value or "0",
                unit=row.unit,
                canonical_unit=canon_result.match.canonical_unit,
            )
        except Exception:
            unmapped_repo.create(
                document_id=document.document_id,
                raw_label=row.label,
                raw_value=row.value,
                raw_unit=row.unit,
                page=row.page,
            )
            unmapped_count += 1
            continue

        if not norm_result.success:
            unmapped_repo.create(
                document_id=document.document_id,
                raw_label=row.label,
                raw_value=row.value,
                raw_unit=row.unit,
                page=row.page,
            )
            unmapped_count += 1
            continue

        # Deduplicate: skip if same biomarker + same value already seen in this document
        dedup_key = (canon_result.match.biomarker_id, norm_result.value_normalized)
        if dedup_key in seen_events:
            continue
        seen_events.add(dedup_key)

        # Create lab event
        event_repo.create(
            biomarker_id=canon_result.match.biomarker_id,
            document_id=document.document_id,
            collected_at=event_date,
            value_original=norm_result.value_original,
            unit_original=norm_result.unit_original,
            value_normalized=norm_result.value_normalized,
            unit_canonical=norm_result.unit_canonical,
            page=row.page,
            lab_name=lab_name,
            confidence=canon_result.match.confidence,
            flag=row.flag,
        )
        events_created += 1

    # Commit all changes
    event_repo.commit()
    unmapped_repo.commit()

    return DocumentUploadResponse(
        document_id=document.document_id,
        filename=document.filename,
        page_count=extraction_result.page_count,
        events_created=events_created,
        unmapped_rows=unmapped_count,
        message=f"Successfully processed {events_created} lab values. {unmapped_count} rows require review.",
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """List documents. When logged in, shows only the user's documents."""
    doc_repo = DocumentRepository(db)
    user_id = current_user.user_id if current_user else None
    documents = doc_repo.get_all(skip=skip, limit=limit, user_id=user_id)

    return [
        DocumentResponse(
            document_id=doc.document_id,
            filename=doc.filename,
            uploaded_at=doc.uploaded_at,
            collected_at=doc.collected_at,
            reported_at=doc.reported_at,
            page_count=doc.page_count,
            event_count=doc_repo.get_event_count(doc.document_id),
            unmapped_count=doc_repo.get_unmapped_count(doc.document_id),
        )
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get document details by ID."""
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_id(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        document_id=document.document_id,
        filename=document.filename,
        uploaded_at=document.uploaded_at,
        collected_at=document.collected_at,
        reported_at=document.reported_at,
        page_count=document.page_count,
        event_count=doc_repo.get_event_count(document.document_id),
        unmapped_count=doc_repo.get_unmapped_count(document.document_id),
    )


@router.get("/{document_id}/events", response_model=list[LabEventResponse])
def get_document_events(
    document_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get all lab events extracted from a document."""
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_id(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    event_repo = LabEventRepository(db)
    events = event_repo.get_by_document(document_id, skip=skip, limit=limit)

    return [
        LabEventResponse(
            event_id=event.event_id,
            biomarker_id=event.biomarker_id,
            analyte_name=event.biomarker.analyte_name,
            category=get_category_for_panel(event.biomarker.panel_seed),
            collected_at=event.collected_at,
            value_normalized=event.value_normalized,
            unit_canonical=event.unit_canonical,
            value_original=event.value_original,
            unit_original=event.unit_original,
            page=event.page,
            confidence=event.confidence,
            flag=event.flag,
        )
        for event in events
    ]


@router.get("/{document_id}/unmapped", response_model=list[UnmappedRowResponse])
def get_unmapped_rows(
    document_id: str,
    status: Optional[str] = Query(
        None, description="Filter by status: pending, resolved, ignored"
    ),
    db: Session = Depends(get_db),
):
    """Get unmapped rows from a document for review."""
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_id(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    unmapped_repo = UnmappedRowRepository(db)
    rows = unmapped_repo.get_by_document(document_id, status=status)

    return [
        UnmappedRowResponse(
            row_id=row.row_id,
            raw_label=row.raw_label,
            raw_value=row.raw_value,
            raw_unit=row.raw_unit,
            page=row.page,
            status=row.status,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/{document_id}/unmapped/{row_id}/resolve")
def resolve_unmapped_row(
    document_id: str,
    row_id: str,
    biomarker_id: str = Query(..., description="Biomarker ID to map to"),
    db: Session = Depends(get_db),
):
    """Manually map an unmapped row to a biomarker from the registry."""
    from app.db.models import BiomarkerRegistry

    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify biomarker exists in registry
    biomarker = db.get(BiomarkerRegistry, biomarker_id)
    if not biomarker:
        raise HTTPException(status_code=404, detail="Biomarker not found in registry")

    unmapped_repo = UnmappedRowRepository(db)
    row = unmapped_repo.resolve(row_id, biomarker_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unmapped row not found")

    # Create a lab event from the resolved row
    normalizer = UnitNormalizer()
    try:
        norm_result = normalizer.normalize(
            value=row.raw_value or "0",
            unit=row.raw_unit,
            canonical_unit=biomarker.canonical_unit,
        )
    except Exception:
        norm_result = None

    if norm_result and norm_result.success:
        # Use document dates: prefer collected_at, fall back to reported_at, then uploaded_at
        collected_at = (
            document.collected_at or document.reported_at or document.uploaded_at
        )

        event_repo = LabEventRepository(db)
        event_repo.create(
            biomarker_id=biomarker_id,
            document_id=document_id,
            collected_at=collected_at,
            value_original=norm_result.value_original,
            unit_original=norm_result.unit_original,
            value_normalized=norm_result.value_normalized,
            unit_canonical=norm_result.unit_canonical,
            page=row.page,
            confidence=1.0,
        )

    unmapped_repo.commit()
    return {"message": "Row resolved successfully", "biomarker_id": biomarker_id}


@router.post("/{document_id}/unmapped/{row_id}/ignore")
def ignore_unmapped_row(
    document_id: str,
    row_id: str,
    db: Session = Depends(get_db),
):
    """Mark an unmapped row as ignored."""
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    unmapped_repo = UnmappedRowRepository(db)
    row = unmapped_repo.ignore(row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unmapped row not found")

    unmapped_repo.commit()
    return {"message": "Row ignored"}


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Delete a document and all associated data."""
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_id(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete the file
    file_path = Path(document.storage_path)
    if file_path.exists():
        file_path.unlink()

    # Delete the record (cascades to events and unmapped rows)
    doc_repo.delete(document_id)

    return {"message": "Document deleted successfully"}
