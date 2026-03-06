"""Seed organ systems, biomarker-system mappings, and correlations.

Usage:
    cd backend && python -m data.seed_graph
"""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import BiomarkerCorrelation, BiomarkerSystemMap, OrganSystem

SEED_FILE = Path(__file__).parent / "organ_systems.json"


def load_seed_data() -> dict:
    with open(SEED_FILE) as f:
        return json.load(f)


def seed_organ_systems(db: Session, data: dict) -> int:
    """Insert organ systems (with children) from seed data."""
    count = 0
    for system in data["systems"]:
        existing = (
            db.query(OrganSystem)
            .filter(OrganSystem.system_id == system["system_id"])
            .first()
        )
        if not existing:
            db.add(
                OrganSystem(
                    system_id=system["system_id"],
                    name=system["name"],
                    description=system.get("description"),
                    parent_system_id=system.get("parent_system_id"),
                )
            )
            count += 1

        # Insert children
        for child in system.get("children", []):
            existing_child = (
                db.query(OrganSystem)
                .filter(OrganSystem.system_id == child["system_id"])
                .first()
            )
            if not existing_child:
                db.add(
                    OrganSystem(
                        system_id=child["system_id"],
                        name=child["name"],
                        description=child.get("description"),
                        parent_system_id=system["system_id"],
                    )
                )
                count += 1

    db.flush()
    return count


def seed_biomarker_mappings(db: Session, data: dict) -> tuple[int, int]:
    """Insert biomarker-to-system mappings. Returns (inserted, skipped)."""
    mappings = data["biomarker_mappings"]
    inserted = 0
    skipped = 0

    for system_id, biomarker_lists in mappings.items():
        if system_id.startswith("_"):
            continue

        for rel_type in ("primary", "secondary"):
            for biomarker_id in biomarker_lists.get(rel_type, []):
                # Check biomarker exists in registry
                from app.db.models import BiomarkerRegistry

                biomarker = (
                    db.query(BiomarkerRegistry)
                    .filter(BiomarkerRegistry.biomarker_id == biomarker_id)
                    .first()
                )
                if not biomarker:
                    skipped += 1
                    continue

                existing = (
                    db.query(BiomarkerSystemMap)
                    .filter(
                        BiomarkerSystemMap.biomarker_id == biomarker_id,
                        BiomarkerSystemMap.system_id == system_id,
                    )
                    .first()
                )
                if not existing:
                    db.add(
                        BiomarkerSystemMap(
                            biomarker_id=biomarker_id,
                            system_id=system_id,
                            relationship_type=rel_type,
                        )
                    )
                    inserted += 1

    db.flush()
    return inserted, skipped


def seed_panel_fallbacks(db: Session, data: dict) -> int:
    """Map remaining unmapped biomarkers using panel_seed → organ system fallback."""
    from app.db.models import BiomarkerRegistry

    fallback = data.get("panel_fallback", {})
    inserted = 0

    # Get already-mapped biomarker IDs
    mapped_ids = {
        row[0] for row in db.query(BiomarkerSystemMap.biomarker_id).distinct().all()
    }

    # Get all biomarkers with their panel_seed
    all_biomarkers = db.query(BiomarkerRegistry).all()

    for biomarker in all_biomarkers:
        if biomarker.biomarker_id in mapped_ids:
            continue

        panel = biomarker.panel_seed or ""
        system_id = fallback.get(panel)
        if not system_id:
            continue

        db.add(
            BiomarkerSystemMap(
                biomarker_id=biomarker.biomarker_id,
                system_id=system_id,
                relationship_type="primary",
            )
        )
        inserted += 1

    db.flush()
    return inserted


def seed_correlations(db: Session, data: dict) -> int:
    """Insert biomarker correlations. Returns count inserted."""
    count = 0
    for corr in data["correlations"]:
        existing = (
            db.query(BiomarkerCorrelation)
            .filter(
                BiomarkerCorrelation.biomarker_id_a == corr["biomarker_id_a"],
                BiomarkerCorrelation.biomarker_id_b == corr["biomarker_id_b"],
            )
            .first()
        )
        if not existing:
            # Verify both biomarkers exist
            from app.db.models import BiomarkerRegistry

            a = (
                db.query(BiomarkerRegistry)
                .filter(BiomarkerRegistry.biomarker_id == corr["biomarker_id_a"])
                .first()
            )
            b = (
                db.query(BiomarkerRegistry)
                .filter(BiomarkerRegistry.biomarker_id == corr["biomarker_id_b"])
                .first()
            )
            if a and b:
                db.add(
                    BiomarkerCorrelation(
                        biomarker_id_a=corr["biomarker_id_a"],
                        biomarker_id_b=corr["biomarker_id_b"],
                        correlation_type=corr["correlation_type"],
                        description=corr.get("description"),
                    )
                )
                count += 1

    db.flush()
    return count


def verify_coverage(db: Session) -> tuple[int, int, list[str]]:
    """Check how many biomarkers have at least one system mapping.

    Returns (mapped_count, total_count, unmapped_ids).
    """
    from app.db.models import BiomarkerRegistry

    all_biomarkers = db.query(BiomarkerRegistry.biomarker_id).all()
    total = len(all_biomarkers)

    mapped = db.query(BiomarkerSystemMap.biomarker_id).distinct().count()

    mapped_ids = {
        row[0] for row in db.query(BiomarkerSystemMap.biomarker_id).distinct().all()
    }
    unmapped = [bid[0] for bid in all_biomarkers if bid[0] not in mapped_ids]

    return mapped, total, unmapped


def main() -> None:
    data = load_seed_data()
    db = SessionLocal()

    try:
        # 1. Seed organ systems
        system_count = seed_organ_systems(db, data)
        print(f"Organ systems: {system_count} inserted")

        # 2. Seed biomarker mappings
        mapped, skipped = seed_biomarker_mappings(db, data)
        print(
            f"Biomarker mappings: {mapped} inserted, {skipped} skipped (not in registry)"
        )

        # 3. Fill gaps via panel_seed fallback
        fallback_count = seed_panel_fallbacks(db, data)
        print(f"Panel fallback mappings: {fallback_count} inserted")

        # 4. Seed correlations
        corr_count = seed_correlations(db, data)
        print(f"Correlations: {corr_count} inserted")

        # 5. Commit
        db.commit()

        # 6. Verify coverage
        mapped_count, total_count, unmapped = verify_coverage(db)
        print(
            f"\nCoverage: {mapped_count}/{total_count} biomarkers mapped to organ systems"
        )
        if unmapped:
            print(f"Unmapped biomarkers ({len(unmapped)}):")
            for bid in sorted(unmapped)[:20]:
                print(f"  {bid}")
            if len(unmapped) > 20:
                print(f"  ... and {len(unmapped) - 20} more")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
