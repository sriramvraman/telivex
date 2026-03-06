"""Document repository - handles Document CRUD operations."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import Document, LabEvent, UnmappedRow


class DocumentRepository:
    """Repository for Document operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        filename: str,
        storage_path: str,
        page_count: Optional[int] = None,
        file_hash: Optional[str] = None,
        collected_at: Optional[datetime] = None,
        reported_at: Optional[datetime] = None,
        user_id: Optional[str] = None,
    ) -> Document:
        """Create a new document record."""
        document = Document(
            document_id=str(uuid.uuid4()),
            filename=filename,
            storage_path=storage_path,
            page_count=page_count,
            file_hash=file_hash,
            uploaded_at=datetime.utcnow(),
            collected_at=collected_at,
            reported_at=reported_at,
            user_id=user_id,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get_by_id(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self.db.get(Document, document_id)

    def get_all(
        self, skip: int = 0, limit: int = 100, user_id: Optional[str] = None
    ) -> list[Document]:
        """Get documents with pagination. If user_id is provided, filter by owner."""
        stmt = select(Document).order_by(Document.uploaded_at.desc())
        if user_id:
            stmt = stmt.where(Document.user_id == user_id)
        stmt = stmt.offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_event_count(self, document_id: str) -> int:
        """Get count of lab events for a document."""
        stmt = (
            select(func.count())
            .select_from(LabEvent)
            .where(LabEvent.document_id == document_id)
        )
        return self.db.scalar(stmt) or 0

    def get_unmapped_count(self, document_id: str) -> int:
        """Get count of unmapped rows for a document."""
        stmt = (
            select(func.count())
            .select_from(UnmappedRow)
            .where(UnmappedRow.document_id == document_id)
        )
        return self.db.scalar(stmt) or 0

    def delete(self, document_id: str) -> bool:
        """Delete a document (cascades to events and unmapped rows)."""
        document = self.get_by_id(document_id)
        if not document:
            return False
        self.db.delete(document)
        self.db.commit()
        return True
