# Telivex

**Extracting Clarity from Clinical History**

Telivex is a patient-controlled longitudinal health reconstruction system. It transforms fragmented medical artifacts—especially laboratory PDFs—into a structured, auditable clinical event ledger.

---

## What Problem Does This Solve?

Medical information in healthcare systems is fragmented across printed reports, PDFs, and disconnected hospital records. Clinicians operate under time pressure and often rely on point-in-time snapshots or patient recall. This leads to:

- Missed trajectories
- Repeated tests
- Incomplete medication histories
- Diagnostic blind spots

**Telivex turns documents into queryable data with full provenance.**

---

## Core Principles

1. **No silent inference** — Ambiguity is surfaced explicitly
2. **Registry-first** — Biomarker identity is authoritative
3. **Full provenance** — Every data point traces to source document + page
4. **Deterministic** — No probabilistic outputs in core pipeline

---

## Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** React (web) + React Native (mobile)
- **Database:** PostgreSQL
- **PDF Extraction:** pdfplumber
- **Storage:** Local filesystem → GCS

---

## Project Structure

```
telivex_health/
├── backend/           # FastAPI application
├── web/               # React web app
├── mobile/            # React Native app (future)
├── docs/              # Documentation & specs
│   ├── specs/         # Product vision, business model
│   ├── sample_pdfs/   # Test PDFs
│   └── ARCHITECTURE.md
├── infra/             # Docker, Terraform (future)
├── .claude/           # AI development context
├── CLAUDE.md          # AI development protocol
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Docker (optional, for local dev)

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m data.seed_registry
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd web
npm install
npm run dev
```

---

## Development

See [CLAUDE.md](./CLAUDE.md) for development protocol and coding standards.

See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for system design.

---

## Phase 1 MVP Scope

- [x] BiomarkerRegistry (76 markers)
- [ ] PDF upload and storage
- [ ] Table extraction (pdfplumber)
- [ ] Canonicalization against registry
- [ ] Unit normalization
- [ ] LabEvent ledger with provenance
- [ ] Trend visualization
- [ ] Evidence drill-down to source PDF

---

## License

Private — All rights reserved.
