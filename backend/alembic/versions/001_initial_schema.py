"""Initial schema - biomarker registry, documents, lab events, unmapped rows

Revision ID: 001
Revises: 
Create Date: 2026-02-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Biomarker Registry
    op.create_table(
        "biomarker_registry",
        sa.Column("biomarker_id", sa.String(255), primary_key=True),
        sa.Column("analyte_name", sa.String(255), nullable=False),
        sa.Column("specimen", sa.String(100), nullable=False),
        sa.Column("measurement_property", sa.String(100), nullable=True),
        sa.Column("canonical_unit", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("panel_seed", sa.String(100), nullable=True),
        sa.Column("is_derived", sa.Boolean(), default=False),
        sa.Column("aliases", postgresql.ARRAY(sa.String()), default=[]),
        sa.Column("default_reference_range_notes", sa.Text(), nullable=True),
    )

    # Documents
    op.create_table(
        "documents",
        sa.Column("document_id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
    )

    # Lab Events
    op.create_table(
        "lab_events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column(
            "biomarker_id",
            sa.String(255),
            sa.ForeignKey("biomarker_registry.biomarker_id"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.document_id"),
            nullable=True,
        ),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.Column("value_original", sa.Float(), nullable=False),
        sa.Column("unit_original", sa.String(50), nullable=False),
        sa.Column("value_normalized", sa.Float(), nullable=False),
        sa.Column("unit_canonical", sa.String(50), nullable=False),
        sa.Column("panel_name", sa.String(100), nullable=True),
        sa.Column("lab_name", sa.String(255), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), default=1.0),
        sa.Column("source_type", sa.String(50), default="pdf_extraction"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("supersedes_event_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_lab_events_biomarker_collected",
        "lab_events",
        ["biomarker_id", "collected_at"],
    )
    op.create_index("ix_lab_events_document", "lab_events", ["document_id"])

    # Unmapped Rows
    op.create_table(
        "unmapped_rows",
        sa.Column("row_id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.document_id"),
            nullable=False,
        ),
        sa.Column("raw_label", sa.String(500), nullable=False),
        sa.Column("raw_value", sa.String(100), nullable=True),
        sa.Column("raw_unit", sa.String(50), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column(
            "resolved_biomarker_id",
            sa.String(255),
            sa.ForeignKey("biomarker_registry.biomarker_id"),
            nullable=True,
        ),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_unmapped_rows_status", "unmapped_rows", ["status"])


def downgrade() -> None:
    op.drop_table("unmapped_rows")
    op.drop_table("lab_events")
    op.drop_table("documents")
    op.drop_table("biomarker_registry")
