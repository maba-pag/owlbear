---
id: 785
title: Schema v9 migration (source_pages, source_id FK)
status: todo
priority: needed
created: '2026-04-10T12:31:05.190224+00:00'
updated: '2026-04-12T20:32:13.171322+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 780
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `schema.py` `SCHEMA_VERSION = 9`
- `_migrate_v8_to_v9()` creates `source_pages` table with columns: `id` (INTEGER PRIMARY KEY), `source_id` (INTEGER REFERENCES knowledge_sources(id)), `url` (TEXT NOT NULL), `content_hash` (TEXT), `last_fetched_at` (TEXT), `status` (TEXT NOT NULL DEFAULT 'pending'), `scope` (TEXT NOT NULL)
- `_migrate_v8_to_v9()` adds `source_id INTEGER REFERENCES knowledge_sources(id)` to `documents` (NULL default, no backfill)
- `_SCOPE_TABLES` updated to include `source_pages`
- All #780 tests pass
- File: `serve/knowledge/src/owlbear_knowledge/schema.py`

## Context
- WS-A: Schema + Models Foundation
- Scope item 5 from #775
- See research F2: NULL source_id for legacy, F6: source_pages ships for Phase 2 readiness

[[2026-04-12]]
## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: `schema.py SCHEMA_VERSION = 9` | STALE — actual constant is `_SCHEMA_VERSION` (private prefix) | AC-CORRECTION: `_SCHEMA_VERSION = 9` |
| AC2: source_pages columns | FAIL — 7 discrepancies with actual DDL | AC-CORRECTION: see column corrections below |
| AC3: documents.source_id INTEGER REFERENCES | FAIL — actual is `source_id TEXT`, no FK constraint | AC-CORRECTION: `source_id TEXT` (nullable, no FK) |
| AC4: _SCOPE_TABLES includes source_pages | PASS | None |
| AC5: All #780 tests pass | PASS — dependency ordering correct | None |
| AC6: File path | PASS | None |

### AC2 Column Corrections Required

AC specifies columns that don't match the actual DDL in `serve/knowledge/src/owlbear_knowledge/schema.py`:

| AC Column | Actual Column | Issue |
|-----------|--------------|-------|
| `id` INTEGER PRIMARY KEY | `id` TEXT PRIMARY KEY | Type mismatch — must be TEXT to match codebase convention |
| `source_id` INTEGER REFERENCES knowledge_sources(id) | `source_id` TEXT | Type mismatch (knowledge_sources.id is TEXT); no FK constraint in SQLite ALTER TABLE |
| `content_hash` TEXT | `extraction_hash` TEXT | Column renamed |
| `last_fetched_at` TEXT | `last_extracted` TEXT | Column renamed |
| `status` TEXT NOT NULL DEFAULT 'pending' | `status` TEXT DEFAULT 'discovered' | Different default, nullable |
| `scope` TEXT NOT NULL | `scope` TEXT DEFAULT 'global' | Has default, nullable |
| (missing) | `created_at` TEXT | Column omitted from AC |
| (missing) | `updated_at` TEXT | Column omitted from AC |

### Corrected AC (for researcher/orchestrator to apply)

Replace AC lines 1-3 with:

- `_SCHEMA_VERSION = 9` in `schema.py`
- `_migrate_v8_to_v9()` creates `source_pages` table with columns: `id` (TEXT PRIMARY KEY), `source_id` (TEXT), `url` (TEXT NOT NULL), `extraction_hash` (TEXT), `last_extracted` (TEXT), `status` (TEXT DEFAULT 'discovered'), `scope` (TEXT DEFAULT 'global'), `created_at` (TEXT), `updated_at` (TEXT)
- `_migrate_v8_to_v9()` adds `source_id TEXT` column to `documents` (NULL default, no backfill, no FK constraint)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Schema migration only |
| Interface clarity | FAIL | AC column types/names wrong vs actual DDL |
| Dependency correctness | PASS | depends_on [780] correct — TDD test-first ordering |
| Module layering | PASS | Single file in knowledge package |
| TDD compliance | PASS | Test task #780 precedes this |
| KISS/YAGNI | PASS | Minimal migration scope |
| Premise challenge | PASS | Implementation already exists, task formalizes pipeline record |
| Pattern consistency | PASS | Follows v5→v6, v6→v7, v7→v8 migration patterns |
| Security surface | PASS | No new external boundaries |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.92) — recommends REFINE, not APPROVE
- Architect response: accepted — implementation task AC must be precise; test task precedent doesn't transfer

### Verdict: REFINE
### Action Taken: Kept in backlog. AC has 7+ factual discrepancies with actual DDL (wrong types, renamed columns, missing columns, wrong defaults). Corrected AC provided above — researcher or orchestrator must update the body before re-submission.
[[2026-04-12]]
## Architecture Review (re-review)

### Prior Review Status
Prior review (2026-04-12) gave REFINE verdict with 7+ AC discrepancies. Corrected AC was provided in task body. Original AC lines at top were never updated, but corrected AC in prior review section is verified accurate against codebase.

### Codebase Verification

Verified against `serve/knowledge/src/owlbear_knowledge/schema.py`:
- `_SCHEMA_VERSION: int = 9` (line 19) — confirmed
- `_CREATE_SOURCE_PAGES` DDL (lines 154-165): `id TEXT PRIMARY KEY`, `source_id TEXT`, `url TEXT NOT NULL`, `status TEXT DEFAULT 'discovered'`, `extraction_hash TEXT`, `last_extracted TEXT`, `scope TEXT DEFAULT 'global'`, `created_at TEXT`, `updated_at TEXT` — all match corrected AC
- `_migrate_v8_to_v9` (lines 251-262): creates source_pages, creates index on source_id, adds `source_id TEXT` to documents via ALTER TABLE (idempotent with contextlib.suppress) — confirmed
- `_SCOPE_TABLES` (lines 22-29): includes `source_pages` — confirmed

### Authoritative AC (builder must follow these, not original AC lines)

- `_SCHEMA_VERSION = 9` in `schema.py`
- `_migrate_v8_to_v9()` creates `source_pages` table with columns: `id` (TEXT PRIMARY KEY), `source_id` (TEXT), `url` (TEXT NOT NULL), `extraction_hash` (TEXT), `last_extracted` (TEXT), `status` (TEXT DEFAULT 'discovered'), `scope` (TEXT DEFAULT 'global'), `created_at` (TEXT), `updated_at` (TEXT)
- `_migrate_v8_to_v9()` adds `source_id TEXT` column to `documents` (NULL default, no backfill, no FK constraint)
- `_SCOPE_TABLES` updated to include `source_pages`
- All #780 tests pass
- File: `serve/knowledge/src/owlbear_knowledge/schema.py`

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Schema migration only |
| Interface clarity | PASS | Corrected AC in body verified against actual DDL |
| Dependency correctness | PASS | depends_on [780] correct — TDD test-first ordering; #780 in todo |
| Module layering | PASS | Single file in knowledge package |
| TDD compliance | PASS | Test task #780 precedes this |
| KISS/YAGNI | PASS | Minimal migration scope |
| Premise challenge | PASS | Implementation already exists; task formalizes pipeline record |
| Pattern consistency | PASS | Follows v5-v6, v6-v7, v7-v8 migration patterns |
| Security surface | PASS | No new external boundaries |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in current session
- Architect response: proceeding — all 10 criteria PASS, corrected AC verified against codebase twice (this review + prior)

### Verdict: APPROVE
### Action Taken: Advanced to todo. Builder must follow the Authoritative AC in this section — not the original AC lines at top of body (which contain stale column names/types). Implementation already landed in schema.py; builder verifies conformance.