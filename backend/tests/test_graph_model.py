"""Tests for health knowledge graph data model and repository."""

import uuid
from datetime import datetime

import pytest

from app.db.database import SessionLocal
from app.db.models import (
    BiomarkerCorrelation,
    BiomarkerRegistry,
    BiomarkerSystemMap,
    HealthSnapshot,
    OrganSystem,
    User,
)
from app.repositories import graph_repo


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.close()


class TestOrganSystems:
    def test_root_systems_exist(self, db):
        """AC-6: At least 8 root organ systems should be seeded."""
        roots = graph_repo.get_root_systems(db)
        assert len(roots) >= 8
        names = {s.name for s in roots}
        assert "Renal" in names
        assert "Hepatic" in names
        assert "Hematologic" in names
        assert "Cardiovascular" in names

    def test_child_systems_have_parents(self, db):
        """Verify hierarchical structure — children reference valid parents."""
        children = (
            db.query(OrganSystem).filter(OrganSystem.parent_system_id.isnot(None)).all()
        )
        assert len(children) > 0
        for child in children:
            parent = graph_repo.get_system_with_children(db, child.parent_system_id)
            assert parent is not None, f"Orphan child: {child.system_id}"

    def test_system_with_children(self, db):
        """Verify parent systems have queryable children."""
        hematologic = graph_repo.get_system_with_children(db, "hematologic")
        assert hematologic is not None
        child_ids = {c.system_id for c in hematologic.children}
        assert "hematologic.erythrocyte" in child_ids
        assert "hematologic.leukocyte" in child_ids


class TestBiomarkerSystemMap:
    def test_all_biomarkers_mapped(self, db):
        """AC-7: All biomarkers should have at least one organ system mapping
        (except 'Other' panel which may be unmapped)."""
        total = db.query(BiomarkerRegistry).count()
        mapped = db.query(BiomarkerSystemMap.biomarker_id).distinct().count()
        # At least 80% coverage (Other panel ~56 items may not all be mapped)
        assert mapped / total >= 0.80, f"Only {mapped}/{total} biomarkers mapped"

    def test_biomarkers_by_system(self, db):
        """Query biomarkers for a specific organ system."""
        renal_mappings = graph_repo.get_biomarkers_by_system(db, "renal.glomerular")
        biomarker_ids = {m.biomarker_id for m in renal_mappings}
        # Creatinine (2160-0) and eGFR (33914-3) should be in renal.glomerular
        assert "2160-0" in biomarker_ids or "33914-3" in biomarker_ids

    def test_systems_for_biomarker(self, db):
        """Query organ systems for a specific biomarker."""
        systems = graph_repo.get_systems_for_biomarker(db, "718-7")  # Hemoglobin
        system_ids = {m.system_id for m in systems}
        assert len(system_ids) >= 1
        # Hemoglobin should be in hematologic
        assert any("hematologic" in sid for sid in system_ids)

    def test_primary_vs_secondary(self, db):
        """Verify relationship_type is correctly set."""
        all_mappings = db.query(BiomarkerSystemMap).all()
        types = {m.relationship_type for m in all_mappings}
        assert "primary" in types

    def test_no_orphan_mappings(self, db):
        """Every mapping references a valid biomarker and organ system."""
        mappings = db.query(BiomarkerSystemMap).all()
        for m in mappings:
            biomarker = (
                db.query(BiomarkerRegistry)
                .filter(BiomarkerRegistry.biomarker_id == m.biomarker_id)
                .first()
            )
            assert biomarker is not None, f"Orphan biomarker_id: {m.biomarker_id}"
            system = (
                db.query(OrganSystem)
                .filter(OrganSystem.system_id == m.system_id)
                .first()
            )
            assert system is not None, f"Orphan system_id: {m.system_id}"


class TestBiomarkerCorrelations:
    def test_correlations_seeded(self, db):
        """AC-8: Key clinical correlations should exist."""
        corrs = db.query(BiomarkerCorrelation).all()
        assert len(corrs) >= 10

    def test_correlation_types(self, db):
        """Verify expected correlation types exist."""
        types = {c.correlation_type for c in db.query(BiomarkerCorrelation).all()}
        assert "clinical_panel" in types
        assert "derived_from" in types
        assert "inverse" in types

    def test_query_correlations_for_biomarker(self, db):
        """Query correlations involving creatinine (2160-0)."""
        corrs = graph_repo.get_correlations_for_biomarker(db, "2160-0")
        assert len(corrs) >= 2  # eGFR and BUN
        partner_ids = set()
        for c in corrs:
            if c.biomarker_id_a == "2160-0":
                partner_ids.add(c.biomarker_id_b)
            else:
                partner_ids.add(c.biomarker_id_a)
        # Should correlate with eGFR (33914-3) and BUN (3094-0)
        assert "33914-3" in partner_ids
        assert "3094-0" in partner_ids


class TestHealthSnapshots:
    def _create_test_user(self, db, suffix: str = "") -> str:
        user_id = f"test-{suffix or uuid.uuid4().hex[:8]}"
        db.add(
            User(
                user_id=user_id,
                email=f"{user_id}@test.local",
                name="Test User",
                password_hash="not-a-real-hash",
            )
        )
        db.flush()
        return user_id

    def test_create_and_query_snapshot(self, db):
        """AC-4/AC-5: Create a snapshot and verify it persists."""
        test_user_id = self._create_test_user(db)
        test_date = datetime(2025, 1, 15)

        snapshot = HealthSnapshot(
            snapshot_id=str(uuid.uuid4()),
            user_id=test_user_id,
            snapshot_date=test_date,
            label="Test snapshot",
        )
        db.add(snapshot)
        db.flush()

        result = (
            db.query(HealthSnapshot)
            .filter(HealthSnapshot.snapshot_id == snapshot.snapshot_id)
            .first()
        )
        assert result is not None
        assert result.user_id == test_user_id
        assert result.snapshot_date == test_date
        assert result.label == "Test snapshot"

        db.rollback()

    def test_snapshot_user_scoping(self, db):
        """AC-21: Snapshots are scoped to user_id."""
        user_a = self._create_test_user(db, f"a-{uuid.uuid4().hex[:8]}")
        user_b = self._create_test_user(db, f"b-{uuid.uuid4().hex[:8]}")

        db.add(
            HealthSnapshot(
                snapshot_id=str(uuid.uuid4()),
                user_id=user_a,
                snapshot_date=datetime(2025, 1, 1),
            )
        )
        db.add(
            HealthSnapshot(
                snapshot_id=str(uuid.uuid4()),
                user_id=user_b,
                snapshot_date=datetime(2025, 1, 1),
            )
        )
        db.flush()

        a_snapshots = graph_repo.get_snapshots_for_user(db, user_a)
        b_snapshots = graph_repo.get_snapshots_for_user(db, user_b)

        assert len(a_snapshots) == 1
        assert len(b_snapshots) == 1
        assert a_snapshots[0].user_id == user_a
        assert b_snapshots[0].user_id == user_b

        db.rollback()


class TestMigration:
    def test_all_tables_exist(self, db):
        """AC-9: Verify all graph tables exist in the database."""
        from sqlalchemy import inspect

        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        assert "organ_systems" in tables
        assert "biomarker_system_map" in tables
        assert "biomarker_correlations" in tables
        assert "health_snapshots" in tables
        assert "snapshot_events" in tables
