"""Add health knowledge graph tables: organ_systems, biomarker_system_map,
biomarker_correlations, health_snapshots, snapshot_events.

Revision ID: 004
Revises: 003
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Organ systems (hierarchical taxonomy)
    op.create_table(
        "organ_systems",
        sa.Column("system_id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column(
            "parent_system_id",
            sa.String(100),
            sa.ForeignKey("organ_systems.system_id"),
        ),
    )

    # Biomarker → Organ system junction
    op.create_table(
        "biomarker_system_map",
        sa.Column(
            "biomarker_id",
            sa.String(255),
            sa.ForeignKey("biomarker_registry.biomarker_id"),
            primary_key=True,
        ),
        sa.Column(
            "system_id",
            sa.String(100),
            sa.ForeignKey("organ_systems.system_id"),
            primary_key=True,
        ),
        sa.Column(
            "relationship_type", sa.String(20), nullable=False, server_default="primary"
        ),
    )
    op.create_index(
        "ix_biomarker_system_map_system", "biomarker_system_map", ["system_id"]
    )

    # Biomarker correlations
    op.create_table(
        "biomarker_correlations",
        sa.Column(
            "biomarker_id_a",
            sa.String(255),
            sa.ForeignKey("biomarker_registry.biomarker_id"),
            primary_key=True,
        ),
        sa.Column(
            "biomarker_id_b",
            sa.String(255),
            sa.ForeignKey("biomarker_registry.biomarker_id"),
            primary_key=True,
        ),
        sa.Column("correlation_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text),
    )

    # Health snapshots (user-scoped point-in-time groupings)
    op.create_table(
        "health_snapshots",
        sa.Column("snapshot_id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.user_id"),
            nullable=False,
        ),
        sa.Column("snapshot_date", sa.DateTime, nullable=False),
        sa.Column("label", sa.String(255)),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_health_snapshots_user_date",
        "health_snapshots",
        ["user_id", "snapshot_date"],
    )

    # Snapshot → LabEvent junction
    op.create_table(
        "snapshot_events",
        sa.Column(
            "snapshot_id",
            sa.String(36),
            sa.ForeignKey("health_snapshots.snapshot_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("lab_events.event_id"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("snapshot_events")
    op.drop_table("health_snapshots")
    op.drop_table("biomarker_correlations")
    op.drop_index("ix_biomarker_system_map_system", "biomarker_system_map")
    op.drop_table("biomarker_system_map")
    op.drop_table("organ_systems")
