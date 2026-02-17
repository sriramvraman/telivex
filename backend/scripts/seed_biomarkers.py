#!/usr/bin/env python3
"""Seed the BiomarkerRegistry from CSV file."""

import csv
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.db.models import BiomarkerRegistry


def parse_aliases(aliases_str: str) -> list[str]:
    """Parse aliases from CSV string format."""
    if not aliases_str or aliases_str.strip() == "":
        return []
    try:
        # Try JSON format first: ["alias1", "alias2"]
        return json.loads(aliases_str)
    except json.JSONDecodeError:
        # Fall back to comma-separated
        return [a.strip() for a in aliases_str.split(",") if a.strip()]


def seed_biomarkers(csv_path: Path, clear_existing: bool = False):
    """Seed biomarkers from CSV file."""
    db = SessionLocal()
    
    try:
        if clear_existing:
            # Delete existing entries
            deleted = db.query(BiomarkerRegistry).delete()
            print(f"Deleted {deleted} existing biomarkers")
            db.commit()
        
        # Read CSV
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            count = 0
            updated = 0
            
            for row in reader:
                biomarker_id = row.get("biomarker_id", "").strip()
                if not biomarker_id:
                    continue
                
                # Check if exists
                existing = db.query(BiomarkerRegistry).filter(
                    BiomarkerRegistry.biomarker_id == biomarker_id
                ).first()
                
                aliases = parse_aliases(row.get("aliases", ""))
                
                if existing:
                    # Update existing
                    existing.analyte_name = row.get("analyte_name", "").strip()
                    existing.specimen = row.get("specimen", "").strip()
                    existing.measurement_property = row.get("measurement_property", "").strip() or None
                    existing.canonical_unit = row.get("canonical_unit", "").strip()
                    existing.category = row.get("category", "").strip() or None
                    existing.panel_seed = row.get("panel_seed", "").strip() or None
                    existing.is_derived = row.get("is_derived", "").lower() == "true"
                    existing.aliases = aliases
                    existing.default_reference_range_notes = row.get("default_reference_range_notes", "").strip() or None
                    updated += 1
                else:
                    # Create new
                    biomarker = BiomarkerRegistry(
                        biomarker_id=biomarker_id,
                        analyte_name=row.get("analyte_name", "").strip(),
                        specimen=row.get("specimen", "").strip(),
                        measurement_property=row.get("measurement_property", "").strip() or None,
                        canonical_unit=row.get("canonical_unit", "").strip(),
                        category=row.get("category", "").strip() or None,
                        panel_seed=row.get("panel_seed", "").strip() or None,
                        is_derived=row.get("is_derived", "").lower() == "true",
                        aliases=aliases,
                        default_reference_range_notes=row.get("default_reference_range_notes", "").strip() or None,
                    )
                    db.add(biomarker)
                    count += 1
            
            db.commit()
            print(f"Seeded {count} new biomarkers, updated {updated} existing")
            
            # Verify
            total = db.query(BiomarkerRegistry).count()
            print(f"Total biomarkers in registry: {total}")
            
    finally:
        db.close()


if __name__ == "__main__":
    csv_path = Path(__file__).parent.parent / "data" / "BiomarkerRegistry_v1.csv"
    
    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}")
        sys.exit(1)
    
    # Use --clear flag to clear existing data first
    clear = "--clear" in sys.argv
    
    print(f"Seeding from: {csv_path}")
    if clear:
        print("Will clear existing data first")
    
    seed_biomarkers(csv_path, clear_existing=clear)
