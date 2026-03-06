# Active Task: STORY-1 — Graph Data Model

## Issue: #2
## Status: In Progress

### Acceptance Criteria
- [ ] AC-1: `organ_systems` table (system_id, name, description, parent_system_id)
- [ ] AC-2: `biomarker_system_map` junction table (biomarker_id, system_id, relationship_type)
- [ ] AC-3: `biomarker_correlations` table (biomarker_id_a, biomarker_id_b, correlation_type, description)
- [ ] AC-4: `health_snapshots` table (snapshot_id, user_id, snapshot_date, label)
- [ ] AC-5: `snapshot_events` junction table (snapshot_id, event_id)
- [ ] AC-6: Organ system taxonomy seeded (8+ systems)
- [ ] AC-7: All biomarkers mapped to at least one organ system
- [ ] AC-8: Key clinical correlations seeded
- [ ] AC-9: Migration applies cleanly
- [ ] AC-10: Migration is reversible
- [ ] AC-11-13: Architecture compliance
- [ ] AC-14-16: Code quality (ruff)
- [ ] AC-17-20: Tests pass
- [ ] AC-21-22: Security (user scoping, no new endpoints)

### Files to Create/Edit
- backend/app/db/models.py — Add new SQLAlchemy models
- backend/alembic/versions/004_*.py — New migration
- backend/app/repositories/graph_repo.py — New repository
- backend/data/organ_systems.json — Seed data
- backend/data/seed_graph.py — Seed script
