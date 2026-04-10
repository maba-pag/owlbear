---
id: 754
title: 'P1-01: Tests — Schema: source type, entity/relation types, source_pages, source_id
  FK'
status: todo
priority: critical
created: '2026-04-10T10:55:24.860558+00:00'
updated: '2026-04-10T12:00:05.982602+00:00'
tags:
- phase-1
- type:test
- scope:knowledge
- schema
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for schema extensions:
1. AUTHENTICATED_WEB in SourceType enum
2. Corporate EntityType values: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
3. Corporate RelationType values: GOVERNS, SUPERSEDES_VERSION
4. SourcePage model: source_id, url, status (discovered/approved/rejected/ingested/stale), extraction_hash, last_extracted
5. source_id FK on documents table
6. Cascade delete from source → pages → documents → entities → edges

All tests fail (RED). No dependency on Phase 0 — schema is needed regardless.

Parent: #751

[[2026-04-10]]
## Research
- Research doc: .owlbear/research/754-schema-extensions-red-tests.md
- Sources: 7 studied, 7 high-relevance (all internal — codebase patterns)
- Recommendation: Write RED tests using established project conventions — `_make_db()` fixture, `TestFromAC_*` class naming, `:memory:` SQLite + `init_db()`. SourcePage status as StrEnum (Option A). Cascade delete as application-level (Option A, matches existing `delete_document_data()` pattern). Schema version v9. (confidence: .85)
- Follow-up tasks created: none — #754 is itself the follow-up from #751 research
- Decision requests: none (T1 — tests for pre-approved schema extensions)

## Challenge Results
- Challenger: FALLBACK — subagent not available
- Confidence in original: .85
- Key findings: all 6 test areas have clear existing patterns to follow; no design ambiguity

### Key Findings
1. Current state: SourceType has 2 members, EntityType 6, RelationType 7. SourcePage model and source_id FK do not exist. Schema at v8.
2. Test patterns well-established: `TestFromAC_*` classes, `_make_db()` helper, enum value assertions, cascade verification via row counts
3. SourcePage status should be a StrEnum (PageStatus) — matches all 3 existing enum conventions
4. Cascade delete should be application-level — matches `DocumentStore.delete_document_data()` pattern, avoids silent DB-level cascades
5. Schema migration v8→v9: one migration covering source_pages table + source_id column on documents
[[2026-04-10]]
## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| 1. AUTHENTICATED_WEB in SourceType enum | PRECISE — single enum member, testable via import + value equality | None |
| 2. Corporate EntityType values (5 members) | PRECISE — all 5 values named explicitly | None |
| 3. Corporate RelationType values (2 members) | PRECISE — GOVERNS, SUPERSEDES_VERSION named explicitly | None |
| 4. SourcePage model fields + PageStatus enum | PRECISE — fields, types, and 5 status values listed | None |
| 5. source_id FK on documents table | PRECISE — testable via PRAGMA table_info introspection | None |
| 6. Cascade delete chain | **REFINED** — original said "source → pages → documents → entities → edges", missing chunks and document_status. Existing `delete_document_data()` tests verify all 5 downstream tables (see tests/test_knowledge_intake_docstore_ingest.py L502-L1112). **Corrected chain:** source → source_pages + documents (via source_id FK) → entities, edges, chunks, document_status. Test must verify all 6 downstream tables have zero rows after source deletion. |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All 6 items are RED tests for schema v9 extensions — one test file, one migration |
| Interface clarity | PASS | After AC #6 refinement, all inputs/outputs/assertions are mechanically derivable |
| Dependency correctness | PASS | `depends_on: []` correct — schema needed regardless of Phase 0 |
| Module layering | PASS | Tests import from `owlbear_knowledge` (correct direction) |
| TDD compliance | PASS | This IS the RED phase test task, tagged `type:test` |
| KISS/YAGNI | PASS | Minimal scope — only tests for pre-approved schema extensions |
| Premise challenge | PASS | Enums/models don't exist yet (verified: SourceType has 2 members, SourcePage absent, no source_id on documents DDL) |
| Pattern consistency | PASS | Research identifies correct patterns: `_make_db()`, `TestFromAC_*`, `:memory:` + `init_db()`, enum value assertions — all verified in tests/test_knowledge_foundation.py and tests/test_knowledge_intake_docstore_ingest.py |
| Security surface | PASS | N/A — RED tests introduce no security surface |
| Single domain | PASS | `scope:knowledge` only |
| Failure mode map | N/A | RED tests don't introduce failure codepaths |
| Decision-request verification | PASS | T1 task — tests for pre-approved schema. No DR needed |
| User-action detection | NOT TRIGGERED | Counter-signal C3: tagged `type:test` |

### AC #6 Refinement (applied)

Original: "Cascade delete from source → pages → documents → entities → edges"

Refined: "Cascade delete: deleting a source removes all associated source_pages, and all documents (via source_id FK on documents), and for each document: entities, edges, chunks, document_status. Test inserts full chain (source → page → document → entity + edge + chunk + document_status), deletes the source, asserts zero rows in all 6 downstream tables."

### Architecture Notes

- Schema migration v8→v9 is correct target — one migration for source_pages table, source_id column on documents, PageStatus enum
- `init_db()` migration ladder pattern in schema.py (L251-L295) is well-established; v9 follows naturally
- No existing `delete` method chains through source → documents; `KnowledgeSourceStore.delete()` only removes the source row (source_store.py L165-171)
- Application-level cascade is the correct pattern — matches `DocumentStore.delete_document_data()` (document_store.py L243-265)

### Challenge Results

- Challenger: FALLBACK — no challenger agent available
- Confidence in approval: .90
- Key risk: none — all patterns well-established, AC now precise

### Verdict: APPROVE
### Action Taken: Refined AC #6 to include full cascade chain (chunks, document_status). Advanced to todo.