# Telivex - AI Development Protocol

**Project:** Patient-controlled longitudinal health reconstruction platform  
**Stack:** FastAPI + React (web) + React Native (mobile) + PostgreSQL

---

## ⚠️ MANDATORY RULES (Cannot Be Overridden)

These rules are **binding** and must be followed at all times.

### 1. CLEARFRAME Mode (Always Active)

You operate in CLEARFRAME analytical mode:
- **Strategic Assertion**: Direct analysis without hedging or softening
- **Truth-First**: Prioritize accuracy over agreement
- **Assumption Challenge**: Flag lazy thinking and unexamined premises
- **Logic Interruption**: Immediately correct logical flaws or conceptual errors
- **No Hedging**: Eliminate unnecessary qualifiers unless logically required
- **Intellectual Honesty**: Default to truth over social preservation
- **Direct Feedback**: Assume emotional resilience and preference for challenge

### 2. Pre-Implementation Checklist (BEFORE Writing Any Code)

**You MUST complete these steps before writing code:**

1. **Check Active Task**
   - Read `.claude/active-task.md`
   - If empty or stale → STOP and ask what to work on

2. **Confirm Scope**
   - Which files will be affected?
   - What are the acceptance criteria?
   - Are there edge cases to handle?

3. **Check for Conflicts**
   - Related work in progress?
   - Database migrations needed?

### 3. Post-Edit Validation (AFTER Every Code Change)

After EVERY response that modifies code:

| File Type | Validation Command |
|-----------|-------------------|
| Python | `ruff check <file>` and `ruff format --check <file>` |
| TypeScript/React | `npx tsc --noEmit` and `npx biome check <file>` |
| SQL migrations | Verify migration runs: `alembic upgrade head` |

**Report errors and FIX before proceeding.**

### 4. Git Workflow

**Commit Message Format:**
```
<type>(<scope>): <description>

<body - explain WHY>

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types:** feat, fix, docs, refactor, test, chore  
**Scopes:** api, extraction, registry, trends, storage, web, mobile, infra, db

**Branch Strategy:**
- `main` - stable, deployable
- `feat/<name>` - feature branches
- `fix/<name>` - bug fixes

### 5. Architecture Compliance

**Backend Layering (STRICT):**
```
API Routes → Services → Repositories → Database
     ↓           ↓            ↓
  Schemas    Business     SQLAlchemy
  (Pydantic)  Logic       Models
```

**Rules:**
- No business logic in API endpoints
- No HTTP concepts (Request, Response) in service layer
- No direct DB access from routes
- All PDF processing in `services/extractor.py`
- All biomarker matching in `services/canonicalizer.py`

**Telivex-Specific Constraints:**
- **No silent inference**: Ambiguity must be surfaced explicitly
- **Registry-first**: Biomarker identity comes from BiomarkerRegistry only
- **Provenance required**: Every LabEvent must trace to source document + page
- **Deterministic only**: No probabilistic outputs in core pipeline

### 6. Data Model Rules

**BiomarkerRegistry is authoritative:**
- Never invent biomarker_ids during extraction
- Unmapped rows → surface for review, don't guess
- Unit conversion must be deterministic (use lookup tables, not inference)

**LabEvent immutability:**
- Events are append-only
- Corrections create new events with `supersedes` field
- Never mutate historical events

---

## Session Start Protocol

At the start of each session:

```bash
# 1. Read current task
cat .claude/active-task.md

# 2. Check git status
git status

# 3. Check for uncommitted work
git diff --stat

# 4. State what you're working on
```

If `.claude/active-task.md` is empty or stale → **STOP and ask** what to work on.

---

## Task Execution Loop

### 1. Before Coding
- Restate acceptance criteria from active-task.md
- Identify verification commands
- If ambiguous → **STOP and ask**

### 2. Implement
- Modify minimal files (1-3 unless justified)
- Write tests for new code
- Follow architecture layering strictly

### 3. Verify
Run verification:
1. Lint: `ruff check` / `biome check`
2. Type check: `mypy` / `tsc`
3. Tests: `pytest` / `npm test`
4. If fail → fix → rerun

### 4. Update
- Check off criteria in `.claude/active-task.md`
- Note any blockers or follow-ups

### 5. Commit
Before committing, verify:
- [ ] All linting errors resolved
- [ ] Tests pass
- [ ] No `print()` / `console.log()` debugging statements
- [ ] No hardcoded secrets or paths
- [ ] Migrations tested (if applicable)

---

## Non-Negotiable Rules

1. **Never declare "done"** without verification commands executed
2. **One task at a time** - complete, verify, commit, then next
3. **Never touch unrelated files** without explicit justification
4. **Always read .claude/active-task.md first** after context loss
5. **Never bypass provenance** - every data point needs a source

---

## Error Recovery

If you make a mistake:
1. Acknowledge it directly (no hedging)
2. Explain what went wrong
3. Fix it immediately
4. Document what you learned in `.claude/learnings.md`

---

## When to Ask Questions

**ASK when:**
- Requirements are ambiguous
- Multiple valid approaches exist
- Change affects data model or schema
- Security/privacy implications unclear
- Biomarker mapping decisions needed

**DON'T ASK when:**
- Standard patterns apply
- User gave explicit instructions
- Bug fix with obvious solution
- Linting/formatting only

---

## Quick Reference

```
Before coding:  ✓ Task file read  ✓ Scope confirmed  ✓ Files identified
During coding:  ✓ Follow architecture  ✓ No shortcuts  ✓ Lint as you go
After coding:   ✓ Lint passes  ✓ Tests pass  ✓ Commit with message
```

---

## Key Files

| File | Purpose |
|------|---------|
| `.claude/active-task.md` | Current task (read FIRST) |
| `.claude/learnings.md` | Lessons learned, gotchas |
| `docs/ARCHITECTURE.md` | System design decisions |
| `backend/data/BiomarkerRegistry_v1.csv` | Authoritative biomarker list |

---

## Project-Specific Commands

```bash
# Start local dev environment
docker-compose up -d

# Run backend
cd backend && uvicorn app.main:app --reload

# Run frontend
cd web && npm run dev

# Database migrations
cd backend && alembic upgrade head

# Seed biomarker registry
cd backend && python -m data.seed_registry

# Run tests
cd backend && pytest -v
cd web && npm test

# Lint everything
cd backend && ruff check . && ruff format --check .
cd web && npx biome check .
```

---

## Domain Glossary

| Term | Definition |
|------|------------|
| **Biomarker** | A measurable indicator (e.g., HbA1c, Creatinine) |
| **LabEvent** | A single biomarker measurement with provenance |
| **Canonicalization** | Matching raw labels to registry biomarker_ids |
| **Provenance** | Source tracing (document_id, page, confidence) |
| **Trend** | Time-series of LabEvents for a single biomarker |
| **Panel** | Group of related tests (e.g., Lipid Profile) |

---

## Phase 1 Acceptance Criteria (MVP)

- [ ] Upload a real lab PDF and extract structured biomarker rows
- [ ] Unmapped labels are visible and not silently ignored
- [ ] Trend queries return deterministic time series with event IDs
- [ ] Each trend point can open the supporting PDF page
- [ ] Unit conversion is deterministic and auditable
