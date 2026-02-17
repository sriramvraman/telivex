"""Document and extraction schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    """Internal model for creating a document."""

    filename: str
    storage_path: str
    page_count: Optional[int] = None
    file_hash: Optional[str] = None


class DocumentResponse(BaseModel):
    """Document response model."""

    document_id: str
    filename: str
    uploaded_at: datetime
    page_count: Optional[int]
    event_count: int = 0
    unmapped_count: int = 0

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    """Response after uploading and processing a document."""

    document_id: str
    filename: str
    page_count: int
    events_created: int
    unmapped_rows: int
    message: str


class ExtractedRow(BaseModel):
    """A single row extracted from PDF table."""

    label: str
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    page: int
    row_index: int


class LabEventCreate(BaseModel):
    """Internal model for creating a lab event."""

    biomarker_id: str
    document_id: str
    collected_at: datetime
    value_original: float
    unit_original: str
    value_normalized: float
    unit_canonical: str
    page: Optional[int] = None
    panel_name: Optional[str] = None
    lab_name: Optional[str] = None
    confidence: float = 1.0


class LabEventResponse(BaseModel):
    """Lab event response model."""

    event_id: str
    biomarker_id: str
    analyte_name: str
    collected_at: datetime
    value_normalized: float
    unit_canonical: str
    value_original: float
    unit_original: str
    page: Optional[int]
    confidence: float

    model_config = {"from_attributes": True}


class UnmappedRowResponse(BaseModel):
    """Unmapped row response model."""

    row_id: str
    raw_label: str
    raw_value: Optional[str]
    raw_unit: Optional[str]
    page: Optional[int]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
