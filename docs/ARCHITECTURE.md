# Telivex Architecture

## Overview

Telivex is a patient-controlled longitudinal health reconstruction system. It transforms fragmented medical artifacts—especially laboratory PDFs—into a structured, auditable clinical event ledger.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Clients                                  │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   React Web     │  React Native   │    WhatsApp (Future)        │
│   (web/)        │  (mobile/)      │                             │
└────────┬────────┴────────┬────────┴─────────────┬───────────────┘
         │                 │                       │
         └─────────────────┼───────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│                        (backend/)                                │
├─────────────────────────────────────────────────────────────────┤
│  API Layer (app/api/routes/)                                    │
│  ├── upload.py      - PDF upload endpoints                      │
│  ├── biomarkers.py  - Registry queries                          │
│  ├── events.py      - LabEvent CRUD                             │
│  └── trends.py      - Trend queries                             │
├─────────────────────────────────────────────────────────────────┤
│  Service Layer (app/services/)                                  │
│  ├── extractor.py     - PDF table extraction (pdfplumber)       │
│  ├── canonicalizer.py - Biomarker matching against registry     │
│  ├── normalizer.py    - Deterministic unit conversion           │
│  └── storage.py       - File storage abstraction                │
├─────────────────────────────────────────────────────────────────┤
│  Repository Layer (app/repositories/)                           │
│  ├── biomarker_repo.py  - BiomarkerRegistry queries             │
│  ├── event_repo.py      - LabEvent persistence                  │
│  └── document_repo.py   - Document metadata                     │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                     │
│  ├── PostgreSQL (structured data)                               │
│  └── Local/GCS (PDF storage)                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### Core Entities

```
┌─────────────────────┐       ┌─────────────────────┐
│  BiomarkerRegistry  │       │      Document       │
├─────────────────────┤       ├─────────────────────┤
│ biomarker_id (PK)   │       │ document_id (PK)    │
│ analyte_name        │       │ filename            │
│ specimen            │       │ storage_path        │
│ measurement_property│       │ uploaded_at         │
│ canonical_unit      │       │ page_count          │
│ category            │       │ user_id (FK)        │
│ aliases[]           │       └──────────┬──────────┘
│ is_derived          │                  │
└──────────┬──────────┘                  │
           │                             │
           │         ┌───────────────────┘
           │         │
           ▼         ▼
┌─────────────────────────────────────────┐
│               LabEvent                   │
├─────────────────────────────────────────┤
│ event_id (PK)                           │
│ biomarker_id (FK)                       │
│ document_id (FK)                        │
│ collected_at                            │
│ value_original + unit_original          │
│ value_normalized + unit_canonical       │
│ panel_name                              │
│ lab_name                                │
│ page                                    │
│ confidence                              │
│ source_type                             │
│ created_at                              │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│            UnmappedRow                   │
├─────────────────────────────────────────┤
│ row_id (PK)                             │
│ document_id (FK)                        │
│ raw_label                               │
│ raw_value                               │
│ raw_unit                                │
│ page                                    │
│ status (pending/resolved/ignored)       │
│ resolved_biomarker_id (FK, nullable)    │
└─────────────────────────────────────────┘
```

---

## Extraction Pipeline

```
PDF Upload
    │
    ▼
┌─────────────────────┐
│  Store PDF          │  → Local filesystem / GCS
│  (storage.py)       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Extract Tables     │  → pdfplumber
│  (extractor.py)     │  → Returns: List[RawRow]
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Canonicalize       │  → Match against BiomarkerRegistry aliases
│  (canonicalizer.py) │  → Returns: (matched[], unmapped[])
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Normalize Units    │  → Deterministic conversion only
│  (normalizer.py)    │  → Fails if conversion unknown
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Persist Events     │  → LabEvents with full provenance
│  (event_repo.py)    │  → UnmappedRows for review
└─────────────────────┘
```

---

## Key Design Decisions

### 1. No Silent Inference
Every ambiguity is surfaced. If a label can't be confidently matched, it goes to UnmappedRow for human review.

### 2. Registry-First Identity
Biomarker identity is authoritative and defined in BiomarkerRegistry. The extraction pipeline cannot invent new biomarker_ids.

### 3. Deterministic Unit Conversion
Unit conversion uses explicit lookup tables, not heuristics. If a conversion path doesn't exist, the event stores original values and flags for review.

### 4. Full Provenance
Every LabEvent traces to: document_id + page + confidence. Users can drill down from any trend point to the source PDF.

### 5. Append-Only Events
LabEvents are immutable after creation. Corrections create new events with a `supersedes` reference.

---

## Technology Choices

| Component | Technology | Rationale |
|-----------|------------|-----------|
| API | FastAPI | Async, type hints, auto docs |
| ORM | SQLAlchemy 2.0 | Mature, async support |
| Migrations | Alembic | Standard for SQLAlchemy |
| PDF Extraction | pdfplumber | Best for tables, deterministic |
| Database | PostgreSQL | Relational integrity, future pgvector |
| Web Frontend | React | Team familiarity, ecosystem |
| Mobile | React Native | Code sharing with web |
| Storage | Local → GCS | Start simple, scale later |

---

## Module Boundaries

### Backend Modules

```
backend/
├── app/
│   ├── api/          # HTTP layer only
│   │   └── routes/   # Endpoint definitions
│   ├── services/     # Business logic
│   ├── repositories/ # Data access
│   ├── schemas/      # Pydantic models (API contracts)
│   └── db/
│       └── models.py # SQLAlchemy models
├── data/             # Seed data, registry CSV
└── tests/
```

**Rule:** Services can call Repositories. Routes can call Services. No skipping layers.

### Frontend Modules

```
web/
├── src/
│   ├── api/          # API client
│   ├── components/   # Reusable UI components
│   ├── pages/        # Route-level components
│   ├── hooks/        # Custom React hooks
│   └── types/        # TypeScript interfaces
```

---

## Future Considerations

### Phase 2: Medication Ledger
- New entity: MedicationEvent
- Temporal alignment with LabEvents
- Active medication snapshot queries

### Phase 3: WhatsApp Ingestion
- Webhook receiver for media messages
- Async extraction queue
- Notification on completion

### Phase 4: Cloud Deployment
- GCS for PDF storage with signed URLs
- Cloud SQL (PostgreSQL)
- Cloud Run for API
- CDN for frontend

### Phase 5: Interoperability
- ABDM/FHIR mapping exploration
- Export formats for clinical use
