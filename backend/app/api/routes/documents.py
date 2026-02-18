"""Document API routes - upload, extraction, and retrieval."""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
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
    collected_date: Optional[str] = Query(
        None, description="Collection date (YYYY-MM-DD) if not in PDF"
    ),
    lab_name: Optional[str] = Query(None, description="Lab name if not in PDF"),
    db: Session = Depends(get_db),
):
    """
    Upload a lab report PDF and extract biomarker data.

    The PDF is processed to extract lab values which are then:
    1. Canonicalized against the BiomarkerRegistry
    2. Normalized to canonical units
    3. Stored as LabEvents with full provenance

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

    # Create document record
    doc_repo = DocumentRepository(db)
    document = doc_repo.create(
        filename=file.filename,
        storage_path=str(file_path),
        page_count=extraction_result.page_count,
        file_hash=file_hash,
    )

    # Initialize services
    canonicalizer = Canonicalizer(db)
    normalizer = UnitNormalizer()
    event_repo = LabEventRepository(db)
    unmapped_repo = UnmappedRowRepository(db)
    
    # DEBUG: Log alias map size
    print(f"DEBUG: Canonicalizer loaded {len(canonicalizer._alias_map)} aliases")
    print(f"DEBUG: Sample aliases - 'rbc count' in map: {'rbc count' in canonicalizer._alias_map}")

    # Parse collected date: user-provided > extracted from PDF > current date
    parsed_date = None
    
    if collected_date:
        # User provided date takes priority
        try:
            parsed_date = datetime.strptime(collected_date, "%Y-%m-%d")
        except ValueError:
            pass
    
    if not parsed_date and extraction_result.collected_date:
        # Try to use date extracted from PDF
        try:
            parsed_date = datetime.strptime(extraction_result.collected_date, "%Y-%m-%d")
        except ValueError:
            pass
    
    if not parsed_date:
        # Default to now if no date found
        parsed_date = datetime.utcnow()

    events_created = 0
    unmapped_count = 0

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
        except Exception as e:
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

        # Create lab event
        event_repo.create(
            biomarker_id=canon_result.match.biomarker_id,
            document_id=document.document_id,
            collected_at=parsed_date,
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
):
    """List all uploaded documents."""
    doc_repo = DocumentRepository(db)
    documents = doc_repo.get_all(skip=skip, limit=limit)

    return [
        DocumentResponse(
            document_id=doc.document_id,
            filename=doc.filename,
            uploaded_at=doc.uploaded_at,
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
