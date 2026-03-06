"""Add LOINC columns to biomarker_registry and clean break for LOINC-native IDs

Revision ID: 002
Revises: 001
Create Date: 2026-03-06

This migration:
1. Drops all lab_events and unmapped_rows (clean break - dev data only)
2. Drops and recreates biomarker_registry with LOINC columns
3. Adds flag column to lab_events (if not present)
4. Re-seed with LOINC-native registry via: python -m data.seed_registry
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "b533b484a72b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clean break: drop dependent tables first
    op.drop_table("unmapped_rows")
    op.drop_table("lab_events")
    op.drop_table("biomarker_registry")

    # Recreate biomarker_registry with LOINC columns
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
        sa.Column("loinc_code", sa.String(20), nullable=True),
        sa.Column("loinc_component", sa.String(255), nullable=True),
        sa.Column("default_reference_range_notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_biomarker_registry_loinc_code", "biomarker_registry", ["loinc_code"])

    # Recreate lab_events with flag column
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
        sa.Column("flag", sa.String(1), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("supersedes_event_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_lab_events_biomarker_collected",
        "lab_events",
        ["biomarker_id", "collected_at"],
    )
    op.create_index("ix_lab_events_document", "lab_events", ["document_id"])

    # Recreate unmapped_rows
    op.create_table(
        "unmapped_rows",
        sa.Column("row_id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.document_id"),
            nullable=False,
        ),
        sa.Column("raw_label", sa.Text(), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
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
    # Drop LOINC-native tables
    op.drop_table("unmapped_rows")
    op.drop_table("lab_events")
    op.drop_table("biomarker_registry")

    # Recreate original schema (without LOINC columns, without flag)
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

    op.create_table(
        "lab_events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("biomarker_id", sa.String(255), sa.ForeignKey("biomarker_registry.biomarker_id"), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.document_id"), nullable=True),
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
    op.create_index("ix_lab_events_biomarker_collected", "lab_events", ["biomarker_id", "collected_at"])
    op.create_index("ix_lab_events_document", "lab_events", ["document_id"])

    op.create_table(
        "unmapped_rows",
        sa.Column("row_id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.document_id"), nullable=False),
        sa.Column("raw_label", sa.String(500), nullable=False),
        sa.Column("raw_value", sa.String(100), nullable=True),
        sa.Column("raw_unit", sa.String(50), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("resolved_biomarker_id", sa.String(255), sa.ForeignKey("biomarker_registry.biomarker_id"), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_unmapped_rows_status", "unmapped_rows", ["status"])
