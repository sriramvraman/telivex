"""
Seed the BiomarkerRegistry table from CSV.
Run: python -m data.seed_registry
"""

import csv
import ast
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import BiomarkerRegistry


def parse_aliases(aliases_str: str) -> list[str]:
    """Parse aliases from CSV string format (supports both Python list and JSON)."""
    if not aliases_str or aliases_str == "[]":
        return []
    try:
        return json.loads(aliases_str)
    except (ValueError, json.JSONDecodeError):
        try:
            return ast.literal_eval(aliases_str)
        except (ValueError, SyntaxError):
            return [aliases_str]


def seed_registry(db: Session, csv_path: Path) -> int:
    """Load biomarkers from CSV into database."""
    count = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            biomarker = BiomarkerRegistry(
                biomarker_id=row["biomarker_id"],
                analyte_name=row["analyte_name"],
                specimen=row["specimen"],
                measurement_property=row.get("measurement_property") or None,
                canonical_unit=row["canonical_unit"],
                category=row.get("category") or None,
                panel_seed=row.get("panel_seed") or None,
                is_derived=row.get("is_derived", "").lower() == "true",
                aliases=parse_aliases(row.get("aliases", "[]")),
                loinc_code=row.get("loinc_code") or None,
                loinc_component=row.get("loinc_component") or None,
                default_reference_range_notes=row.get("default_reference_range_notes")
                or None,
            )

            # Upsert - update if exists
            existing = (
                db.query(BiomarkerRegistry)
                .filter(BiomarkerRegistry.biomarker_id == biomarker.biomarker_id)
                .first()
            )
            if existing:
                for key, value in vars(biomarker).items():
                    if not key.startswith("_"):
                        setattr(existing, key, value)
            else:
                db.add(biomarker)
            count += 1

    db.commit()
    return count


def main():
    # Use LOINC-native v2 registry if available, fall back to v1
    data_dir = Path(__file__).parent
    csv_path = data_dir / "BiomarkerRegistry_v2_loinc.csv"
    if not csv_path.exists():
        csv_path = data_dir / "BiomarkerRegistry_v1.csv"
    if not csv_path.exists():
        print(f"ERROR: No registry CSV found in {data_dir}")
        return

    db = SessionLocal()
    try:
        count = seed_registry(db, csv_path)
        print(f"Seeded {count} biomarkers from {csv_path.name}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
