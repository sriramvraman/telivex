"""Repository for health knowledge graph queries."""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import (
    BiomarkerCorrelation,
    BiomarkerSystemMap,
    HealthSnapshot,
    LabEvent,
    OrganSystem,
    SnapshotEvent,
)


def get_all_systems(db: Session) -> list[OrganSystem]:
    """Return all organ systems ordered by name."""
    return db.query(OrganSystem).order_by(OrganSystem.name).all()


def get_root_systems(db: Session) -> list[OrganSystem]:
    """Return top-level organ systems (no parent)."""
    return (
        db.query(OrganSystem)
        .filter(OrganSystem.parent_system_id.is_(None))
        .order_by(OrganSystem.name)
        .all()
    )


def get_system_with_children(db: Session, system_id: str) -> OrganSystem | None:
    """Return an organ system with its children loaded."""
    return db.query(OrganSystem).filter(OrganSystem.system_id == system_id).first()


def get_biomarkers_by_system(
    db: Session, system_id: str, include_secondary: bool = True
) -> list[BiomarkerSystemMap]:
    """Return all biomarker mappings for a given organ system."""
    query = db.query(BiomarkerSystemMap).filter(
        BiomarkerSystemMap.system_id == system_id
    )
    if not include_secondary:
        query = query.filter(BiomarkerSystemMap.relationship_type == "primary")
    return query.all()


def get_systems_for_biomarker(
    db: Session, biomarker_id: str
) -> list[BiomarkerSystemMap]:
    """Return all organ system mappings for a given biomarker."""
    return (
        db.query(BiomarkerSystemMap)
        .filter(BiomarkerSystemMap.biomarker_id == biomarker_id)
        .all()
    )


def get_correlations_for_biomarker(
    db: Session, biomarker_id: str
) -> list[BiomarkerCorrelation]:
    """Return all correlations involving a given biomarker."""
    return (
        db.query(BiomarkerCorrelation)
        .filter(
            (BiomarkerCorrelation.biomarker_id_a == biomarker_id)
            | (BiomarkerCorrelation.biomarker_id_b == biomarker_id)
        )
        .all()
    )


def create_snapshot(
    db: Session,
    user_id: str,
    snapshot_date: datetime,
    event_ids: list[str],
    label: str | None = None,
) -> HealthSnapshot:
    """Create a health snapshot grouping lab events from the same collection date."""
    snapshot = HealthSnapshot(
        snapshot_id=str(uuid.uuid4()),
        user_id=user_id,
        snapshot_date=snapshot_date,
        label=label,
    )
    db.add(snapshot)
    db.flush()

    for event_id in event_ids:
        db.add(SnapshotEvent(snapshot_id=snapshot.snapshot_id, event_id=event_id))

    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_snapshots_for_user(db: Session, user_id: str) -> list[HealthSnapshot]:
    """Return all snapshots for a user, ordered by date descending."""
    return (
        db.query(HealthSnapshot)
        .filter(HealthSnapshot.user_id == user_id)
        .order_by(HealthSnapshot.snapshot_date.desc())
        .all()
    )


def auto_create_snapshots(db: Session, user_id: str) -> list[HealthSnapshot]:
    """Auto-generate snapshots by grouping lab events by collection date.

    Only creates snapshots for dates that don't already have one.
    """
    # Find distinct collection dates for this user's events
    existing_dates = {
        s.snapshot_date
        for s in db.query(HealthSnapshot)
        .filter(HealthSnapshot.user_id == user_id)
        .all()
    }

    # Get all events for this user via documents
    from app.db.models import Document

    events = (
        db.query(LabEvent)
        .join(LabEvent.document)
        .filter(Document.user_id == user_id)
        .order_by(LabEvent.collected_at)
        .all()
    )

    # Group by date (not datetime)
    by_date: dict[datetime, list[str]] = {}
    for event in events:
        date_key = datetime(
            event.collected_at.year,
            event.collected_at.month,
            event.collected_at.day,
        )
        if date_key not in existing_dates:
            by_date.setdefault(date_key, []).append(event.event_id)

    snapshots = []
    for date, event_ids in by_date.items():
        label = f"Lab results — {date.strftime('%d %b %Y')}"
        snapshot = HealthSnapshot(
            snapshot_id=str(uuid.uuid4()),
            user_id=user_id,
            snapshot_date=date,
            label=label,
        )
        db.add(snapshot)
        db.flush()
        for event_id in event_ids:
            db.add(SnapshotEvent(snapshot_id=snapshot.snapshot_id, event_id=event_id))
        snapshots.append(snapshot)

    if snapshots:
        db.commit()
        for s in snapshots:
            db.refresh(s)

    return snapshots
