from pydantic import BaseModel


class BiomarkerResponse(BaseModel):
    """Response schema for a biomarker."""

    biomarker_id: str
    analyte_name: str
    specimen: str
    measurement_property: str | None
    canonical_unit: str
    category: str | None
    panel_seed: str | None
    is_derived: bool
    aliases: list[str]
    default_reference_range_notes: str | None

    class Config:
        from_attributes = True


class BiomarkerListResponse(BaseModel):
    """Response schema for listing biomarkers."""

    biomarkers: list[BiomarkerResponse]
    total: int
