# Active Task

## Current Task
**Phase 1B: PDF Extraction Pipeline**

### Description
Implement the core PDF processing pipeline: upload, extract tables, canonicalize biomarkers, normalize units, and create LabEvents with full provenance.

### Acceptance Criteria
- [ ] PDF upload endpoint (`POST /api/v1/documents/upload`)
- [ ] Document stored with metadata (filename, upload_date, page_count)
- [ ] pdfplumber table extraction service
- [ ] Canonicalization service (match raw labels → registry biomarker_ids using aliases)
- [ ] Unit normalization service (deterministic conversion tables)
- [ ] LabEvent creation with provenance (document_id, page, row_index)
- [ ] UnmappedRow surfacing (rows that couldn't be matched)
- [ ] GET endpoint to list unmapped rows for review

### Files to Modify/Create
- `backend/app/api/v1/documents.py` - Upload endpoint
- `backend/app/services/extractor.py` - PDF table extraction
- `backend/app/services/canonicalizer.py` - Biomarker matching
- `backend/app/services/normalizer.py` - Unit conversion
- `backend/app/repositories/document_repo.py` - Document CRUD
- `backend/app/repositories/lab_event_repo.py` - LabEvent CRUD
- `backend/app/schemas/document.py` - Request/response schemas

### Verification Commands
```bash
# Lint
cd backend && ruff check app/ && ruff format --check app/

# Type check
cd backend && mypy app/

# Test upload with sample PDF
curl -X POST -F "file=@sample.pdf" http://localhost:8001/api/v1/documents/upload

# Check extracted events
curl http://localhost:8001/api/v1/documents/{id}/events

# Check unmapped rows
curl http://localhost:8001/api/v1/documents/{id}/unmapped
```

---

## Task History

| Date | Task | Status |
|------|------|--------|
| 2026-02-17 | Phase 1A: Foundation | ✅ Complete |
| 2026-02-17 | Phase 1B: PDF Extraction Pipeline | 🚧 In Progress |
