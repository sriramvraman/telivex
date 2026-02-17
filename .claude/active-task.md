# Active Task

## Current Task
**Phase 1B: PDF Extraction Pipeline** 🚧 IN PROGRESS

### Description
Implement the core PDF processing pipeline: upload, extract tables, canonicalize biomarkers, normalize units, and create LabEvents with full provenance.

### Acceptance Criteria
- [x] PDF upload endpoint (`POST /api/v1/documents/upload`)
- [x] Document stored with metadata (filename, upload_date, page_count, file_hash)
- [x] pdfplumber table extraction service
- [x] Canonicalization service (match raw labels → registry biomarker_ids using aliases)
- [x] Unit normalization service (deterministic conversion tables)
- [x] LabEvent creation with provenance (document_id, page, row_index)
- [x] UnmappedRow surfacing (rows that couldn't be matched)
- [x] GET endpoint to list unmapped rows for review
- [ ] **PENDING: Integration test with real PDF**
- [ ] **PENDING: Verify database migrations work**

### Files Created
- `backend/app/api/routes/documents.py` - Upload and retrieval endpoints
- `backend/app/services/extractor.py` - PDF table extraction with pdfplumber
- `backend/app/services/canonicalizer.py` - Biomarker matching against registry
- `backend/app/services/normalizer.py` - Unit conversion (deterministic)
- `backend/app/repositories/document_repo.py` - Document CRUD
- `backend/app/repositories/lab_event_repo.py` - LabEvent & UnmappedRow CRUD
- `backend/app/schemas/document.py` - Request/response schemas

### Verification Commands (TO RUN)
```bash
# 1. Ensure DB is running
docker compose up -d

# 2. Run migrations
cd backend && source .venv/bin/activate && alembic upgrade head

# 3. Start API
uvicorn app.main:app --reload --port 8001

# 4. Test upload (need a sample PDF)
curl -X POST -F "file=@sample_lab_report.pdf" \
  "http://localhost:8001/api/v1/documents/upload?collected_date=2026-01-15"

# 5. Check extracted events
curl http://localhost:8001/api/v1/documents/{id}/events

# 6. Check unmapped rows
curl http://localhost:8001/api/v1/documents/{id}/unmapped
```

---

## Task History

| Date | Task | Status |
|------|------|--------|
| 2026-02-17 | Phase 1A: Foundation | ✅ Complete |
| 2026-02-17 | Phase 1B: PDF Extraction Pipeline | 🚧 Code complete, needs testing |
