---
id: 1589
title: 'Consolidation test: knowledge DB integrity hardening'
status: review
priority: important
created: 2026-05-15T16:25:02.116082+00:00
updated: 2026-05-16T14:06:52.349088+00:00
tags:
  - consolidation-test
  - scope:knowledge
  - type:test
  - db-integrity
parent: 1580
depends_on:
  - 1586
  - 1588
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Parent: #1580

Scope:
- In scope: Integration test that exercises schema constraints and audit function together end-to-end.
- Out of scope: Unit-level constraint tests (covered by #1585), unit-level audit tests (covered by #1587).

Acceptance Criteria:
AC-1: Test initializes a fresh v13 knowledge database via `init_db(conn)`, inserts a document→chunk→entity→edge chain using `DocumentStore.insert_document()`, `DocumentStore.store_chunks()`, and `DocumentStore.store_extractions()`, creates a `document_status` entry via `DocumentStore.set_status()`, calls `audit_integrity(conn)`, and asserts `count == 0` for all four categories: `chunks_orphaned`, `entities_orphaned`, `edges_dangling`, `status_orphaned`.
AC-2: Test creates orphan rows in all four audit categories (orphan chunk, orphan entity, dangling edge, orphan document_status) by executing direct SQL with `PRAGMA foreign_keys = OFF`, re-enables FK enforcement, calls `audit_integrity(conn)`, and asserts each category's `count` equals the number of orphans injected in that category and `ids` contains the injected row IDs.

Proof bundle: behavioral

Builder Guidance:
- Use `_NullVectorStore` and `_NullEmbedder` stubs matching the pattern in `tests/test_schema_constraint_enforcement_1586.py`.
- `GraphStore(conn)` is the only graph_store dependency needed.
- For AC-2, insert orphan rows directly (e.g., chunk with non-existent document_id, entity with non-existent document_id, edge with non-existent source_id/target_id, document_status with non-existent document_id).
- Import `audit_integrity` from `owlbear_knowledge.integrity` (canonical path per #1588).
- Import `init_db` from `owlbear_knowledge.schema`.

[[2026-05-16T15:43:25+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single consolidation test exercising two dependencies together |
| Interface clarity | PASS (after REFINE) | AC names exact functions, methods, and assertion targets |
| Dependency correctness | PASS | #1586 (archived), #1588 (archived) — both completed |
| Module layering | PASS | Test-only task within knowledge domain |
| TDD compliance | PASS | Tagged `type:test` — test-writer passes through, builder writes test |
| KISS/YAGNI | PASS | Minimal scope — two AC lines, one integration test file |
| Premise challenge | PASS | Consolidation test adds unique value: proves full DocumentStore API chain + audit_integrity work together (not covered by unit tests in #1585/#1586/#1587/#1588 individually) |
| Pattern consistency | PASS | Follows existing test patterns (stubs, init_db usage) from #1586 |
| Security surface | N/A | Read-only test, no new system boundaries |
| Single domain | PASS | Knowledge module only |

### Design Diverge
- Trigger: skipped — single approach (init_db fresh v13 + API chain + audit)

### Challenge Results
- Challenger: reconsider (confidence 0.55)
- Valid findings addressed:
  1. "v12 schema" incorrect → fixed to "v13 via init_db()"
  2. document_status path never exercised → added set_status() to AC-1 chain
  3. "DocumentStore APIs" insufficiently specific → enumerated exact methods
  4. "source→" prefix not auditable → removed from chain description
  5. AC-2 didn't enumerate all 4 categories → now requires orphans in all four categories with count+ids verification
- Dismissed: migration-path argument — migration is already covered by 17 tests in #1586. Consolidation value is proving API chain + audit work together on hardened schema, not re-testing migration.
- Architect response: accepted findings 1-5, rebutted migration path concern

### Proof-Bundle Validation
- Planner assignment: behavioral (body only)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PASS-THROUGH (type:test tag)

### Verdict: APPROVED (after REFINE)
### Action Taken: Refined ACs to fix schema version (v12→v13), enumerate exact DocumentStore methods, include document_status path, require all 4 orphan categories in AC-2 with ids assertion, added builder guidance. Set proof_bundle frontmatter. Advanced to todo.

[[2026-05-16T15:44:03+02:00]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — no tests applicable.
- Passing through to builder.
- Builder will write the consolidation integration test exercising the full DocumentStore API chain + `audit_integrity` per AC-1 and AC-2.

[[2026-05-16T15:51:23+02:00]]
## Builder Notes
- Implementation: added tests/test_knowledge_integrity_consolidation_1589.py
- AC mapping:
  - AC-1 covered by `test_ac1_clean_chain_returns_zero_for_all_audit_categories` using `init_db(conn)`, `DocumentStore.insert_document()`, `store_chunks()`, `store_extractions()`, `set_status()`, and `audit_integrity(conn)` with zero-count assertions for `chunks_orphaned`, `entities_orphaned`, `edges_dangling`, `status_orphaned`.
  - AC-2 covered by `test_ac2_orphan_rows_are_detected_with_counts_and_ids` by inserting orphan chunk/entity/edge/document_status rows under `PRAGMA foreign_keys = OFF`, re-enabling FK, then asserting per-category `count == 1` and injected IDs present.
- Tests (quality-runner scoped): 2 passed, 0 failed
- Lint (quality-runner scoped): clean
- Coverage: quality-runner reported module coverage not emitted for this scoped run (`owlbear_knowledge.integrity` shown as not in report); implementation touched test file only.
- Module-level durable tests: no `serve/knowledge/tests/*integrity*.py` durable file found; skipped per workflow.
- Commit: a33a5e5563f2dc81d767e0bd2e05d2717d142f39

[[2026-05-16T16:03:50+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1589 -> todo | AC-1 proof is insufficient because the test only checks zero orphan counts after the API calls; it does not directly prove the created rows exist, so `set_status()` can no-op and still green.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1: fresh v13 DB, insert document→chunk→entity→edge chain via `DocumentStore`, create `document_status` via `set_status()`, audit clean, assert zero counts | `audit_integrity()` only reports orphan/dangling row counts and ids in `serve/knowledge/src/owlbear_knowledge/integrity.py` (lines 11, 16, 29, 42, 56, 71-84). `document_status` is a standalone table with `document_id TEXT PRIMARY KEY` and no FK in `serve/knowledge/src/owlbear_knowledge/schema.py` (lines 97-98). The row-creation path for status is `StatusStore.set_status()` in `serve/knowledge/src/owlbear_knowledge/status_store.py` (lines 72, 90, 97). | `test_ac1_clean_chain_returns_zero_for_all_audit_categories` calls `insert_document`, `store_chunks`, `store_extractions`, and `set_status` in `tests/test_knowledge_integrity_consolidation_1589.py` (lines 57, 66, 81, 87), then asserts only the four zero counts (lines 91-94). There is no direct assertion that the `document_status` row or the inserted chain rows exist before auditing. | FAIL |
| AC-2: inject all four orphan categories via direct SQL with FK off, re-enable, audit, assert per-category count and ids | `audit_integrity()` surfaces the four requested categories in `serve/knowledge/src/owlbear_knowledge/integrity.py` (lines 16, 29, 42, 56, 71-84). | `test_ac2_orphan_rows_are_detected_with_counts_and_ids` asserts both `count == 1` and injected ids for all four categories in `tests/test_knowledge_integrity_consolidation_1589.py` (lines 96, 133-143). | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The test proves only that `audit_integrity()` reported zero orphan/dangling rows, not that the `document_status` row and API-created chain actually exist. Because `document_status` has no FK and the test performs no direct presence assertions, `set_status()` could stop inserting rows and this test would still pass. | `tests/test_knowledge_integrity_consolidation_1589.py` lines 57, 66, 81, 87, 91-94; `serve/knowledge/src/owlbear_knowledge/schema.py` lines 97-98; `serve/knowledge/src/owlbear_knowledge/status_store.py` lines 72, 90, 97; `serve/knowledge/src/owlbear_knowledge/integrity.py` lines 11-84 | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen AC-1 proof so the consolidation test directly verifies the rows created by the API chain before auditing, at minimum the `document_status` row created by `set_status()` and preferably the inserted document/chunk/entity/edge chain that AC-1 says is created. | tests/test_knowledge_integrity_consolidation_1589.py | AC-1; `tests/test_knowledge_integrity_consolidation_1589.py` lines 57, 66, 81, 87, 91-94; `serve/knowledge/src/owlbear_knowledge/schema.py` lines 97-98; `serve/knowledge/src/owlbear_knowledge/status_store.py` lines 72, 90, 97 |

## Observations
- AC-2 proof is strong: each injected orphan category is asserted on both `count` and injected `id` membership in `tests/test_knowledge_integrity_consolidation_1589.py` (lines 133-143).
- Builder evidence on scoped tests and lint was internally consistent enough for a static review; no independent `quality-runner` rerun was needed because the blocker is visible from the test logic itself.
- Challenger cross-check agreed with the fail direction and narrowed the clean blocker to AC-1 row-presence proof, especially around `set_status()`.

[[2026-05-16T16:06:52+02:00]]
## Test-Writer Notes
- Retry: strengthened AC-1 proof with direct row-presence assertions.
- File: `tests/test_knowledge_integrity_consolidation_1589.py`
- Class: `TestFromAC_KnowledgeIntegrityConsolidation1589`
- Changes: added 6 direct SQL assertions to `test_ac1_clean_chain_returns_zero_for_all_audit_categories` that verify rows exist BEFORE calling `audit_integrity`:
  - `documents` row present (guards `insert_document()`)
  - `chunks` row present for doc_id (guards `store_chunks()`)
  - `entities` row present for entity-1589 (guards `store_extractions()`)
  - `edges` row present for edge-1589 (guards `store_extractions()`)
  - `document_status` row present for doc_id (guards `set_status()`)
  - `document_status.status == "done"` value check (guards correct status storage)
- Quality-runner: 2 passed, 0 failed, lint clean
- Builder skip: test-only retry — all new assertions PASS against current implementation (implementation is correct; the weakness was proof-gap only).
- AC coverage:
  | AC | Tests | Status |
  |---|---|---|
  | AC-1: clean chain → zero audit counts | `test_ac1_...` (2 passes, now with row-presence guards) | PASS |
  | AC-2: orphan injection → detected with counts+ids | `test_ac2_...` | PASS (unchanged) |
- Commit: 18f8bab
