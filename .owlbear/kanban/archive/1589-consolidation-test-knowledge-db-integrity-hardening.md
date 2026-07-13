---
id: 1589
title: 'Consolidation test: knowledge DB integrity hardening'
status: archived
priority: medium
created: 2026-05-15T16:25:02.116082+00:00
updated: 2026-05-17T00:44:46.635917+00:00
tags:
  - consolidation-test
  - scope:knowledge
  - type:test
  - db-integrity
parent: 1580
depends_on:
  - 1586
  - 1588
ac:
  - 'AC-1: A SINGLE test function performs ALL of AC-1a through AC-1c in one setup.
    Init fresh v13 DB via `init_db(conn)`, insert document→chunk→entity→edge chain
    via `DocumentStore.insert_document()`, `store_chunks()`, `store_extractions()`,
    create document_status via `set_status(doc_id, "done")`.'
  - 'AC-1a: Same function asserts row existence: document row with `content` field
    matching the intake content (proving `insert_document()` wrote it — `store_chunks()`
    backfill writes empty content), chunk row by `chunk_ids[0]` (NOT by document_id
    lookup), entity row, edge row, document_status row.'
  - 'AC-1b: Same function asserts linkage fields: `chunks.document_id == doc_id`,
    `entities.document_id == doc_id`, `entities.chunk_id == chunk_ids[0]`, `edges.source_id
    == entity_id`, `edges.target_id == entity_id`, `edges.document_id == doc_id`,
    `document_status.status == "done"`.'
  - 'AC-1c: Same function calls `audit_integrity(conn)` AFTER all linkage assertions
    and asserts `count == 0` for `chunks_orphaned`, `entities_orphaned`, `edges_dangling`,
    `status_orphaned`.'
  - 'AC-2: Test injects orphan rows in all four audit categories via direct SQL with
    `PRAGMA foreign_keys = OFF`, re-enables FK, calls `audit_integrity(conn)`, asserts
    each category `count` equals injected count and `ids` contains injected row IDs.'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
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

[[2026-05-16T16:23:22+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1589 -> backlog | AC-1 still lacks task-local proof that the revised test persists the document→chunk→entity→edge linkage; second review cycle routes to backlog.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1: fresh v13 DB, insert document→chunk→entity→edge chain via DocumentStore, create document_status via set_status, audit clean, assert zero counts | `store_extractions()` stamps entity `document_id`/`chunk_id` and edge provenance before persisting via GraphStore in `serve/knowledge/src/owlbear_knowledge/document_store.py:231-256`; GraphStore persists entity linkage fields and edge source/target/document fields in `serve/knowledge/src/owlbear_knowledge/graph_store.py:85-105` and `serve/knowledge/src/owlbear_knowledge/graph_store.py:198-221`. `audit_integrity()` only checks `chunks.document_id`, `entities.document_id`, dangling non-null `edge.source_id`/`edge.target_id`, and `document_status.document_id` in `serve/knowledge/src/owlbear_knowledge/integrity.py:11-69`. | The retry now proves document, chunk, entity, edge, and document_status row existence before audit in `tests/test_knowledge_integrity_consolidation_1589.py:92-106`, then asserts the four zero counts in `tests/test_knowledge_integrity_consolidation_1589.py:108-113`. But it never asserts `entities.document_id`/`entities.chunk_id` or `edges.source_id`/`edges.target_id`/`edges.document_id`, so the named chain linkage is still not directly proved. | FAIL |
| AC-2: inject all four orphan categories via direct SQL with FK off, re-enable, audit, assert per-category count and ids | `audit_integrity()` returns the four requested categories in `serve/knowledge/src/owlbear_knowledge/integrity.py:11-69`. | `tests/test_knowledge_integrity_consolidation_1589.py:123-162` disables FK checks, inserts orphan chunk/entity/edge/status rows, re-enables FK, and asserts both `count == 1` and injected ID membership for all four categories. | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The retry closes the original `set_status()` no-op gap, but it still only proves row existence, not the document→chunk→entity→edge linkage the AC names. A regression that dropped or corrupted `entities.chunk_id`, `edges.source_id`/`target_id`, or `edges.document_id` could still pass because the test only checks row existence and `audit_integrity()` does not validate those fields. | `tests/test_knowledge_integrity_consolidation_1589.py:98-106`; `serve/knowledge/src/owlbear_knowledge/document_store.py:231-256`; `serve/knowledge/src/owlbear_knowledge/graph_store.py:85-105`; `serve/knowledge/src/owlbear_knowledge/graph_store.py:198-221`; `serve/knowledge/src/owlbear_knowledge/integrity.py:33-60` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC-1 proof expectations for the consolidation chain and require task-local assertions on the persisted linkage/provenance fields that make the document→chunk→entity→edge chain real before re-dispatching. | .owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md; tests/test_knowledge_integrity_consolidation_1589.py | AC-1; `tests/test_knowledge_integrity_consolidation_1589.py:98-106`; `serve/knowledge/src/owlbear_knowledge/document_store.py:231-256`; `serve/knowledge/src/owlbear_knowledge/integrity.py:33-60` |

## Observations
- The previous blocker around `set_status()` is fixed: the retry now asserts a `document_status` row exists and that its stored status equals `"done"` in `tests/test_knowledge_integrity_consolidation_1589.py:104-106`.
- AC-2 proof remains strong and specific: each injected orphan category is checked for both exact count and injected ID membership in `tests/test_knowledge_integrity_consolidation_1589.py:152-162`.
- Builder/test-writer quality evidence was internally consistent, so no independent `quality-runner` rerun was needed; the remaining blocker is visible from static proof inspection.
- Adversarial cross-checks split on severity: challenger treated the remaining gap as medium but non-blocking, while code-reader judged it blocking under a strict task-local AC-1 reading. This review adopts the stricter reading because the task is a consolidation test whose unique value is proving the chain itself, not just row existence plus clean audit counts.

[[2026-05-16T16:25:00+02:00]]
## Architecture Review (cycle 2)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single consolidation test — purpose is proving end-to-end chain linkage |
| Interface clarity | PASS (after REFINE) | AC-1a/b/c now enumerates exact fields and values for linkage proof |
| Dependency correctness | PASS | #1586 (archived), #1588 (archived) — both completed |
| Module layering | PASS | Test-only task within knowledge domain |
| TDD compliance | PASS | Tagged `type:test` — test-writer passes through, builder writes test |
| KISS/YAGNI | PASS | Minimal scope — adds ~5 explicit linkage assertions to existing test |
| Premise challenge | PASS | Consolidation test proves chain linkage not covered by unit tests or audit_integrity alone |
| Pattern consistency | PASS | Follows existing test patterns from #1586 |
| Security surface | N/A | Read-only test |
| Single domain | PASS | Knowledge module only |

### Reviewer Feedback Integration
Reviewer rejected (cycle 2) because AC-1 required only row-existence assertions but not proof of actual linkage/provenance fields that `store_extractions()` stamps:
- `entities.chunk_id` — not audited by `audit_integrity()` at all
- `edges.document_id` — not checked by edge audit (only source_id/target_id → entities)
- `chunks.document_id` — covered by audit orphan check, but explicit assertion proves chain direction
- `document_status.status` value — proves `set_status()` stored correct value, not just a row

Refined AC-1 → AC-1a/b/c now requires 7 explicit linkage field assertions before calling audit, closing all false-green paths.

### Challenge Results
- Challenger: ac-quality (confidence 0.64)
- Valid findings addressed:
  1. `set_status()` value proof missing → added `document_status.status == \"done\"` to AC-1b
  2. `chunks.document_id` not in draft → added to AC-1b
  3. \"reference the created entity\" too interpretive → replaced with `edges.source_id == entity_id`, `edges.target_id == entity_id`
- Rebutted: B1 compound-AC concern — consolidation tests exist to prove the full chain in one pass; splitting defeats purpose

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PASS-THROUGH (type:test tag)

### Builder Guidance (updated)
- Extend `test_ac1_...` with linkage field assertions:
  - `chunks.document_id == doc_id`
  - `entities.document_id == doc_id`
  - `entities.chunk_id == chunk_ids[0]`
  - `edges.source_id == \"entity-1589\"`
  - `edges.target_id == \"entity-1589\"`
  - `edges.document_id == doc_id`
  - `document_status.status == \"done\"` (likely already present)
- Some assertions may already exist from prior retries; only add what's missing.

### Verdict: APPROVED (after REFINE)
Action: Refined AC to require explicit linkage field assertions, closing false-green paths. Re-approved to todo.

[[2026-05-16T16:31:20+02:00]]
## Architecture Review (cycle 2) — Summary
Refined AC-1 into AC-1a/b/c to require 7 explicit linkage field assertions (chunks.document_id, entities.document_id, entities.chunk_id, edges.source_id, edges.target_id, edges.document_id, document_status.status) BEFORE calling audit_integrity. Closes all false-green paths identified by reviewer in cycles 1 and 2. Challenger findings (ac-quality, 0.64) integrated. AC-2 unchanged.

[[2026-05-16T16:36:14+02:00]]
## Test-Writer Notes
- Retry (cycle 3): added AC-1b linkage field test method.
- File: `tests/test_knowledge_integrity_consolidation_1589.py`
- Class: `TestFromAC_KnowledgeIntegrityConsolidation1589`
- New method: `test_ac1b_chain_linkage_fields_are_set_before_audit`
- Changes: adds 7 explicit linkage field assertions BEFORE calling audit_integrity, covering all AC-1b requirements:
  - `chunks.document_id == doc_id`
  - `entities.document_id == doc_id`
  - `entities.chunk_id == chunk_ids[0]`
  - `edges.source_id == entity_id`
  - `edges.target_id == entity_id`
  - `edges.document_id == doc_id`
  - `document_status.status == "done"`
- Also asserts `audit_integrity()` zero counts after linkage checks (AC-1c).
- Quality-runner (scoped): 3 passed, 0 failed, lint clean.
- Builder skip: test-only retry — all new assertions PASS against current implementation (linkage fields are correctly stamped by `store_extractions()`). Direct-to-review advance per Step 1b.1.
- AC coverage:
  | AC | Tests | Status |
  |---|---|---|
  | AC-1a: API-created rows exist | `test_ac1_...` (existing) | PASS |
  | AC-1b: linkage fields before audit | `test_ac1b_...` (new) | PASS |
  | AC-1c: zero audit counts after linkage | `test_ac1b_...` (new, includes audit assert) | PASS |
  | AC-2: orphan injection detected | `test_ac2_...` (existing) | PASS |
- Commit: 53c396dde191624b3fdb5f9a365d9ac1882a03dc

[[2026-05-16T16:48:01+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1589 -> backlog | AC-1 still diverges from the refined contract: chunk proof is not by `chunk_ids[0]`, and the required one-pass AC-1 proof is split across two fresh-DB tests.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1a: row existence for document, chunk (by `chunk_ids[0]`), entity, edge, document_status | Refined task AC requires the created chunk to be asserted by `chunk_ids[0]` in `.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md:18`. | `test_ac1_clean_chain_returns_zero_for_all_audit_categories` proves document/entity/edge/status row presence, but the chunk check is `SELECT id FROM chunks WHERE document_id = ?` in `tests/test_knowledge_integrity_consolidation_1589.py:95`, which only proves some chunk exists for the document. | FAIL |
| AC-1b / AC-1c: same test asserts linkage before audit, then runs clean audit in that same setup | Refined task AC requires the same test to assert linkage before audit in `.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md:22` and then call `audit_integrity(conn)` after linkage in `.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md:26`. The architecture retry notes also say consolidation must prove the full chain in one pass and explicitly instruct extending `test_ac1_...` in `.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md:224` and `.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md:232`. | Row-existence plus zero-count audit live in `test_ac1_clean_chain_returns_zero_for_all_audit_categories` at `tests/test_knowledge_integrity_consolidation_1589.py:52` and `tests/test_knowledge_integrity_consolidation_1589.py:92-113`, while linkage plus zero-count audit live in separate `test_ac1b_chain_linkage_fields_are_set_before_audit` at `tests/test_knowledge_integrity_consolidation_1589.py:115` and `tests/test_knowledge_integrity_consolidation_1589.py:154-181`. That split across two fresh-DB tests diverges from the refined one-pass proof contract. | FAIL |
| AC-2: inject all four orphan categories and assert exact counts + IDs | `audit_integrity()` exposes the four categories in `serve/knowledge/src/owlbear_knowledge/integrity.py:11-69`. | `test_ac2_orphan_rows_are_detected_with_counts_and_ids` asserts exact count and injected-ID membership for all four categories in `tests/test_knowledge_integrity_consolidation_1589.py:183-229`. | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1a | The chunk presence check does not assert the created chunk by `chunk_ids[0]`; it only proves any chunk row exists for the document, which is weaker than the refined AC. | `.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md:18`; `tests/test_knowledge_integrity_consolidation_1589.py:95` | backlog |
| 2 | AC-1b, AC-1c | The refined contract requires one end-to-end AC-1 test. Current proof splits row-existence and linkage/audit across two fresh-DB tests, despite the architect explicitly rejecting split proof and instructing the existing `test_ac1_...` to be extended. | `.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md:22`; `.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md:26`; `.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md:224`; `.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md:232`; `tests/test_knowledge_integrity_consolidation_1589.py:52`; `tests/test_knowledge_integrity_consolidation_1589.py:115`; `tests/test_knowledge_integrity_consolidation_1589.py:154-181` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope AC-1 for a single end-to-end proof shape and re-dispatch with explicit wording that the existing `test_ac1_...` must carry row-existence, linkage, and clean-audit assertions in one setup. | .owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md; tests/test_knowledge_integrity_consolidation_1589.py | AC-1a/AC-1b/AC-1c; task lines 18, 22, 26, 224, 232; test lines 52, 95, 115, 154-181 |
| 2 | architect | Preserve the refined `chunk_ids[0]` requirement in the next dispatch so the row-presence proof checks the created chunk, not any chunk for the document. | .owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md; tests/test_knowledge_integrity_consolidation_1589.py | AC-1a; task line 18; test line 95 |

## Observations
- AC-2 proof remains strong and specific: each injected orphan category is checked for exact count and injected-ID membership in `tests/test_knowledge_integrity_consolidation_1589.py:183-229`.
- The earlier `set_status()` false-green is fixed: the current tests assert stored status `"done"` in `tests/test_knowledge_integrity_consolidation_1589.py:106` and `tests/test_knowledge_integrity_consolidation_1589.py:174`.
- Builder/test-writer quality evidence was internally consistent, so no independent `quality-runner` rerun was needed; the blocker is visible from the current test structure and assertions.
- Challenger cross-check returned `reconsider` (0.83 confidence) and agreed the remaining issue is contract compliance, not a source behavior defect.

2026-05-16T14:49:34+00:00
## Architecture Review (cycle 3)

### Reviewer Feedback Integration
Reviewer rejected (cycle 3) for two contract compliance issues:
1. Chunk presence check uses `WHERE document_id = ?` instead of asserting by `chunk_ids[0]` directly.
2. AC-1 proof is split across two test functions (`test_ac1_...` and `test_ac1b_...`) despite AC saying \"Same test.\"

Root cause: the \"Same test\" language in AC-1b/AC-1c was ambiguous — builder interpreted it as \"same class\" not \"same function.\" Fixed by:
- Consolidated AC-1a/b/c under a preamble AC-1 that says \"A SINGLE test function performs ALL of AC-1a through AC-1c in one setup.\"
- AC-1a explicitly says chunk row checked \"by `chunk_ids[0]` (NOT by document_id lookup).\"

### Builder Guidance (cycle 3)
- **MERGE** the current `test_ac1b_chain_linkage_fields_are_set_before_audit` INTO `test_ac1_clean_chain_returns_zero_for_all_audit_categories`. Delete the separate `test_ac1b_...` method.
- The resulting single function must: (1) setup chain, (2) assert row existence including chunk by `chunk_ids[0]`, (3) assert all 7 linkage fields, (4) call `audit_integrity` and assert zero counts.
- For chunk row existence, use: `conn.execute(\"SELECT id FROM chunks WHERE id = ?\", (chunk_ids[0],)).fetchone()` — NOT `WHERE document_id = ?`.
- The two existing test methods cover the right assertions individually; this is purely a merge + fix the chunk lookup.

### Verdict: APPROVED (after REFINE)
Action: Rewrote AC-1 preamble to mandate single-function proof shape; fixed chunk lookup requirement to use `chunk_ids[0]` identity; updated builder guidance to merge existing methods. Re-approved to todo.

[[2026-05-16T16:49:41+02:00]]
## Architecture Review (cycle 3)
Refined AC-1a/b/c preamble to explicitly mandate a SINGLE test function for the full chain proof. Fixed two ambiguities that caused 3 review cycles:
1. \"Same test\" → \"A SINGLE test function performs ALL of AC-1a through AC-1c in one setup\"
2. Chunk lookup → \"by `chunk_ids[0]` (NOT by document_id lookup)\"

Builder guidance updated: merge `test_ac1b_...` into `test_ac1_...`, fix chunk assertion to use ID lookup. AC-2 unchanged.

Proof bundle: behavioral
Test-writer: PASS-THROUGH (type:test tag)

[[2026-05-16T17:05:03+02:00]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — pass-through to builder.
- Architecture Review cycle 3 (2026-05-16T16:49) explicitly confirms: "Test-writer: PASS-THROUGH (type:test tag)".
- Reviewer findings in cycles 1–3 are test-structure quality issues (wrong chunk lookup query, split proof across two methods), not missing tests. Per Step 1b: builder addresses code-quality findings.
- Builder guidance (cycle 3) is clear: MERGE `test_ac1b_chain_linkage_fields_are_set_before_audit` INTO `test_ac1_clean_chain_returns_zero_for_all_audit_categories`; fix chunk lookup to `WHERE id = ?` with `chunk_ids[0]`; delete `test_ac1b_...` method.

[[2026-05-16T17:08:01+02:00]]
## Builder Notes
- Files changed:
  - tests/test_knowledge_integrity_consolidation_1589.py
- Implementation summary:
  - Merged AC-1 proof into a SINGLE function (`test_ac1_clean_chain_returns_zero_for_all_audit_categories`) per cycle-3 architecture guidance.
  - Fixed chunk row-existence assertion to use `chunk_ids[0]` identity lookup (`SELECT id FROM chunks WHERE id = ?`) instead of document-level lookup.
  - Moved AC-1b linkage/provenance assertions into the same AC-1 function before `audit_integrity(conn)`.
  - Removed split method `test_ac1b_chain_linkage_fields_are_set_before_audit` to satisfy the one-function proof shape.
- AC mapping:
  - AC-1 / AC-1a / AC-1b / AC-1c: covered in single method `test_ac1_clean_chain_returns_zero_for_all_audit_categories`.
  - AC-2: unchanged and still covered in `test_ac2_orphan_rows_are_detected_with_counts_and_ids`.
- Quality evidence (quality-runner, scoped):
  - Baseline before edit: 3 passed, 0 failed, lint clean.
  - Post-edit verification: 2 passed, 0 failed, lint clean.
  - Coverage report: overall 27% for `owlbear_knowledge (total)`; `owlbear_knowledge.integrity` not separately listed in this scoped run.
- Module-level durable test check:
  - No `serve/knowledge/tests/test*integrity*.py` durable file found; skipped per workflow.
- Commit:
  - 508d6059 `test: merge AC-1 consolidation proof into single function (#1589, builder)`

[[2026-05-16T17:58:17+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1589 -> backlog | AC-1 still has a false-green around `insert_document()`: `store_chunks()` can backfill the document row, so the current proof can pass even if `insert_document()` regresses to a no-op.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1: A SINGLE test function performs ALL of AC-1a through AC-1c in one setup using `insert_document()`, `store_chunks()`, `store_extractions()`, and `set_status()` | Refined contract requires one AC-1 function in [.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md#L18](.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md#L18). | The file now has a single AC-1 function at [tests/test_knowledge_integrity_consolidation_1589.py#L52](tests/test_knowledge_integrity_consolidation_1589.py#L52). | PASS |
| AC-1a: Same function asserts row existence, including the document row and chunk row by `chunk_ids[0]` | `insert_document()` is the path that writes the intake-backed document payload in [serve/knowledge/src/owlbear_knowledge/document_store.py#L70](serve/knowledge/src/owlbear_knowledge/document_store.py#L70) and [serve/knowledge/src/owlbear_knowledge/document_store.py#L75](serve/knowledge/src/owlbear_knowledge/document_store.py#L75)-[serve/knowledge/src/owlbear_knowledge/document_store.py#L77](serve/knowledge/src/owlbear_knowledge/document_store.py#L77), but `store_chunks()` can independently create a minimal documents row in [serve/knowledge/src/owlbear_knowledge/document_store.py#L104](serve/knowledge/src/owlbear_knowledge/document_store.py#L104). | The test calls `insert_document()` at [tests/test_knowledge_integrity_consolidation_1589.py#L57](tests/test_knowledge_integrity_consolidation_1589.py#L57), then `store_chunks()` at [tests/test_knowledge_integrity_consolidation_1589.py#L66](tests/test_knowledge_integrity_consolidation_1589.py#L66), and only later checks document-row existence by id at [tests/test_knowledge_integrity_consolidation_1589.py#L90](tests/test_knowledge_integrity_consolidation_1589.py#L90)-[tests/test_knowledge_integrity_consolidation_1589.py#L91](tests/test_knowledge_integrity_consolidation_1589.py#L91). The chunk row, entity row, edge row, and status row checks are present at [tests/test_knowledge_integrity_consolidation_1589.py#L93](tests/test_knowledge_integrity_consolidation_1589.py#L93)-[tests/test_knowledge_integrity_consolidation_1589.py#L104](tests/test_knowledge_integrity_consolidation_1589.py#L104), but no assertion distinguishes a real `insert_document()` write from the later `store_chunks()` backfill. | FAIL |
| AC-1b: Same function asserts linkage fields before audit | `store_extractions()` stamps document/chunk provenance in [serve/knowledge/src/owlbear_knowledge/document_store.py#L231](serve/knowledge/src/owlbear_knowledge/document_store.py#L231) and [serve/knowledge/src/owlbear_knowledge/document_store.py#L236](serve/knowledge/src/owlbear_knowledge/document_store.py#L236)-[serve/knowledge/src/owlbear_knowledge/document_store.py#L237](serve/knowledge/src/owlbear_knowledge/document_store.py#L237), and persists edge/document linkage via [serve/knowledge/src/owlbear_knowledge/document_store.py#L250](serve/knowledge/src/owlbear_knowledge/document_store.py#L250)-[serve/knowledge/src/owlbear_knowledge/document_store.py#L256](serve/knowledge/src/owlbear_knowledge/document_store.py#L256). | The required linkage assertions are present before audit at [tests/test_knowledge_integrity_consolidation_1589.py#L109](tests/test_knowledge_integrity_consolidation_1589.py#L109), [tests/test_knowledge_integrity_consolidation_1589.py#L116](tests/test_knowledge_integrity_consolidation_1589.py#L116)-[tests/test_knowledge_integrity_consolidation_1589.py#L117](tests/test_knowledge_integrity_consolidation_1589.py#L117), and [tests/test_knowledge_integrity_consolidation_1589.py#L124](tests/test_knowledge_integrity_consolidation_1589.py#L124)-[tests/test_knowledge_integrity_consolidation_1589.py#L126](tests/test_knowledge_integrity_consolidation_1589.py#L126). | PASS |
| AC-1c: Same function audits after linkage assertions and expects zero orphan/dangling counts | `audit_integrity()` exposes the four required categories in [serve/knowledge/src/owlbear_knowledge/integrity.py#L11](serve/knowledge/src/owlbear_knowledge/integrity.py#L11)-[serve/knowledge/src/owlbear_knowledge/integrity.py#L84](serve/knowledge/src/owlbear_knowledge/integrity.py#L84). | The audit is called after the linkage checks at [tests/test_knowledge_integrity_consolidation_1589.py#L128](tests/test_knowledge_integrity_consolidation_1589.py#L128), and the test asserts zero counts for all four categories at [tests/test_knowledge_integrity_consolidation_1589.py#L130](tests/test_knowledge_integrity_consolidation_1589.py#L130)-[tests/test_knowledge_integrity_consolidation_1589.py#L133](tests/test_knowledge_integrity_consolidation_1589.py#L133). | PASS |
| AC-2: Inject all four orphan categories with FK off, then assert exact counts and IDs | `audit_integrity()` reports `chunks_orphaned`, `entities_orphaned`, `edges_dangling`, and `status_orphaned` in [serve/knowledge/src/owlbear_knowledge/integrity.py#L16](serve/knowledge/src/owlbear_knowledge/integrity.py#L16), [serve/knowledge/src/owlbear_knowledge/integrity.py#L29](serve/knowledge/src/owlbear_knowledge/integrity.py#L29), [serve/knowledge/src/owlbear_knowledge/integrity.py#L42](serve/knowledge/src/owlbear_knowledge/integrity.py#L42), and [serve/knowledge/src/owlbear_knowledge/integrity.py#L56](serve/knowledge/src/owlbear_knowledge/integrity.py#L56). | The AC-2 test disables FK enforcement, injects all four orphan categories, then asserts exact counts and injected IDs at [tests/test_knowledge_integrity_consolidation_1589.py#L143](tests/test_knowledge_integrity_consolidation_1589.py#L143) and [tests/test_knowledge_integrity_consolidation_1589.py#L172](tests/test_knowledge_integrity_consolidation_1589.py#L172)-[tests/test_knowledge_integrity_consolidation_1589.py#L182](tests/test_knowledge_integrity_consolidation_1589.py#L182). | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 / AC-1a | The document-row proof is not uniquely coupled to `insert_document()`. A regression where `insert_document()` becomes a no-op would still pass because `store_chunks()` can synthesize the documents row later, and the test only checks `documents.id` existence after both calls. This leaves AC-1 with a remaining false-green despite the cycle-3 structural fixes. | [.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md#L18](.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md#L18); [tests/test_knowledge_integrity_consolidation_1589.py#L57](tests/test_knowledge_integrity_consolidation_1589.py#L57); [tests/test_knowledge_integrity_consolidation_1589.py#L66](tests/test_knowledge_integrity_consolidation_1589.py#L66); [tests/test_knowledge_integrity_consolidation_1589.py#L90](tests/test_knowledge_integrity_consolidation_1589.py#L90)-[tests/test_knowledge_integrity_consolidation_1589.py#L91](tests/test_knowledge_integrity_consolidation_1589.py#L91); [serve/knowledge/src/owlbear_knowledge/document_store.py#L70](serve/knowledge/src/owlbear_knowledge/document_store.py#L70); [serve/knowledge/src/owlbear_knowledge/document_store.py#L75](serve/knowledge/src/owlbear_knowledge/document_store.py#L75)-[serve/knowledge/src/owlbear_knowledge/document_store.py#L77](serve/knowledge/src/owlbear_knowledge/document_store.py#L77); [serve/knowledge/src/owlbear_knowledge/document_store.py#L104](serve/knowledge/src/owlbear_knowledge/document_store.py#L104) | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC-1a so the consolidation proof must verify a document field combination that only `insert_document()` can satisfy, or explicitly relax the contract if document-row existence alone is intended. Then re-dispatch with that clarified proof shape. | .owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md; tests/test_knowledge_integrity_consolidation_1589.py; serve/knowledge/src/owlbear_knowledge/document_store.py | AC-1 / AC-1a; [.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md#L18](.owlbear/kanban/tasks/1589-consolidation-test-knowledge-db-integrity-hardening.md#L18); [tests/test_knowledge_integrity_consolidation_1589.py#L57](tests/test_knowledge_integrity_consolidation_1589.py#L57), [tests/test_knowledge_integrity_consolidation_1589.py#L66](tests/test_knowledge_integrity_consolidation_1589.py#L66), [tests/test_knowledge_integrity_consolidation_1589.py#L90](tests/test_knowledge_integrity_consolidation_1589.py#L90)-[tests/test_knowledge_integrity_consolidation_1589.py#L91](tests/test_knowledge_integrity_consolidation_1589.py#L91); [serve/knowledge/src/owlbear_knowledge/document_store.py#L70](serve/knowledge/src/owlbear_knowledge/document_store.py#L70), [serve/knowledge/src/owlbear_knowledge/document_store.py#L75](serve/knowledge/src/owlbear_knowledge/document_store.py#L75)-[serve/knowledge/src/owlbear_knowledge/document_store.py#L77](serve/knowledge/src/owlbear_knowledge/document_store.py#L77), [serve/knowledge/src/owlbear_knowledge/document_store.py#L104](serve/knowledge/src/owlbear_knowledge/document_store.py#L104) |

## Observations
- The cycle-3 structural blockers are fixed: AC-1 is back to a single test function at [tests/test_knowledge_integrity_consolidation_1589.py#L52](tests/test_knowledge_integrity_consolidation_1589.py#L52), the chunk existence check now uses `chunk_ids[0]` at [tests/test_knowledge_integrity_consolidation_1589.py#L93](tests/test_knowledge_integrity_consolidation_1589.py#L93)-[tests/test_knowledge_integrity_consolidation_1589.py#L94](tests/test_knowledge_integrity_consolidation_1589.py#L94), and the linkage/audit ordering matches the refined contract.
- AC-2 proof remains strong and specific: exact counts plus injected-ID membership are asserted for all four categories at [tests/test_knowledge_integrity_consolidation_1589.py#L172](tests/test_knowledge_integrity_consolidation_1589.py#L172)-[tests/test_knowledge_integrity_consolidation_1589.py#L182](tests/test_knowledge_integrity_consolidation_1589.py#L182).
- Builder evidence on scoped tests and lint was internally consistent, so no independent `quality-runner` rerun was needed. The blocker is visible from static proof inspection.
- Behavioral-bundle challenger review returned `reconsider`, and an additional code-reader cross-check reached the same remaining blocker: the current AC-1 proof still cannot distinguish `insert_document()` from the `store_chunks()` document backfill path.

[[2026-05-16T18:00:00+02:00]]
## Architecture Review (cycle 4)

### Reviewer Feedback Integration
Reviewer rejected (cycle 4) because AC-1a document-row proof only checks `documents.id` existence, which `store_chunks()` backfill can satisfy independently of `insert_document()`.

Root cause analysis:
- `insert_document()` writes: `content=intake.content`, `title=intake.source`, `metadata=json.dumps(intake.metadata)`, `scope`, `source_id`
- `store_chunks()` backfill writes: `content=''`, `title=''`, `metadata='{}'`, no `scope`/`source_id`
- The discriminating field is `documents.content` — non-empty only when `insert_document()` created the row.

Fix: AC-1a now requires asserting `documents.content` matches the intake content, closing the last false-green path.

### Builder Guidance (cycle 4)
- Change the document row-existence check from `SELECT id FROM documents WHERE id = ?` to `SELECT content FROM documents WHERE id = ?` and assert `content == \"hello integrity\"` (the intake content value used in the test setup).
- This is a single-line change in the existing assertion block (~line 90-91).
- All other assertions (chunk by `chunk_ids[0]`, entity, edge, status, linkage fields, audit) remain unchanged.

### Proof-Bundle Validation
- Final bundle: behavioral
- Test-writer: PASS-THROUGH (type:test tag)

### Challenge Results
- Challenger: SKIPPED — minimal delta from cycle-3 approval (single column addition to existing SELECT); prior 3 challenger runs validated overall design.

### Verdict: APPROVED (after REFINE)
Action: Refined AC-1a to require `documents.content` field assertion, closing the `store_chunks()` backfill false-green path. Re-approved to todo.

[[2026-05-16T18:24:51+02:00]]
## Architecture Review (cycle 4)
Refined AC-1a to require `documents.content` field assertion matching intake payload. This closes the last false-green: `store_chunks()` backfill writes `content=''`, so asserting non-empty content uniquely proves `insert_document()` created the row. Single-line change for builder.

Proof bundle: behavioral
Test-writer: PASS-THROUGH (type:test tag)

[[2026-05-16T19:24:11+02:00]]
## Test-Writer Notes
- Retry cycle 5: PASS-THROUGH — `type:test` tag; Architecture Review cycle 4 (2026-05-16T18:24) explicitly confirms "Test-writer: PASS-THROUGH (type:test tag)".
- Reviewer finding is **weak-test / false-green path** (not missing tests): current `SELECT id FROM documents WHERE id = ?` does not discriminate `insert_document()` from `store_chunks()` backfill. Per Step 1b, code-quality findings pass to builder.
- File: `tests/test_knowledge_integrity_consolidation_1589.py`
- Class: `TestFromAC_KnowledgeIntegrityConsolidation1589`

**Builder action required (single-line change per architect cycle 4 guidance):**
- Line ~91: change `SELECT id FROM documents WHERE id = ?` → `SELECT content FROM documents WHERE id = ?`
- Change assertion: `assert doc_row is not None` → `assert doc_row is not None` PLUS `assert doc_row[0] == "hello integrity"` (or update the query to fetch `content` and assert its value)
- All other assertions (chunk by `chunk_ids[0]`, entity, edge, status, all 7 linkage fields, audit zero counts, AC-2) remain unchanged.

**AC coverage (current state):**
| AC | Tests | Status |
|---|---|---|
| AC-1 / AC-1a: document row with `content` field assertion | `test_ac1_...` — missing `content` check | FAIL (false-green risk) |
| AC-1b: linkage fields before audit | `test_ac1_...` lines 107–128 | PASS |
| AC-1c: zero audit counts after linkage | `test_ac1_...` lines 130–133 | PASS |
| AC-2: orphan injection → detected with counts+ids | `test_ac2_...` | PASS |

[[2026-05-16T20:25:45+02:00]]
## Builder Notes
- Files changed: tests/test_knowledge_integrity_consolidation_1589.py
- Implementation summary:
  - Refined AC-1a document assertion to uniquely prove `insert_document()` persistence path.
  - Changed query from `SELECT id FROM documents WHERE id = ?` to `SELECT content FROM documents WHERE id = ?`.
  - Added explicit value assertion `doc_row[0] == "hello integrity"` to ensure intake content is persisted and prevent false-green via `store_chunks()` backfill.
- AC mapping:
  - AC-1 / AC-1a: now proves document row exists with expected content, chunk row by `chunk_ids[0]`, entity row, edge row, and status row.
  - AC-1b / AC-1c: existing linkage and post-linkage audit-zero assertions unchanged and preserved.
  - AC-2: orphan injection and count/id assertions unchanged and preserved.
- Quality evidence (quality-runner, scoped):
  - Baseline before edit: 2 passed, 0 failed; lint clean.
  - Post-edit verification: 2 passed, 0 failed; lint clean.
  - Coverage: scoped run reported overall 27%; module-specific coverage entry for `owlbear_knowledge.integrity` not emitted in final run output.
- Module-level durable test check:
  - No `serve/knowledge/tests/test*integrity*.py` durable file found; skipped per workflow.
- Commit:
  - f7cd800e586467c8945a1b54fd719c52582fd839

[[2026-05-16T22:30:57+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1589 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: scoped quality-runner reported 2 passed, 0 failed, lint clean; the live file state matches the builder note.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 / AC-1a | `insert_document()` writes the document row in `serve/knowledge/src/owlbear_knowledge/document_store.py:70`; the known `store_chunks()` backfill path writes empty content in `serve/knowledge/src/owlbear_knowledge/document_store.py:104`. | The single AC-1 function in `tests/test_knowledge_integrity_consolidation_1589.py:52` calls `insert_document()`, `store_chunks()`, `store_extractions()`, and `set_status()`, then proves `documents.content` at `tests/test_knowledge_integrity_consolidation_1589.py:90`, chunk existence by `chunk_ids[0]` at `tests/test_knowledge_integrity_consolidation_1589.py:94`, and entity/edge/status row existence at `tests/test_knowledge_integrity_consolidation_1589.py:97`, `tests/test_knowledge_integrity_consolidation_1589.py:100`, and `tests/test_knowledge_integrity_consolidation_1589.py:103`. | PASS |
| AC-1b | `store_extractions()` persists entity/edge linkage through `serve/knowledge/src/owlbear_knowledge/document_store.py:207`, `serve/knowledge/src/owlbear_knowledge/graph_store.py:85`, and `serve/knowledge/src/owlbear_knowledge/graph_store.py:198`; `set_status()` persists status in `serve/knowledge/src/owlbear_knowledge/status_store.py:72`. | The same AC-1 function asserts chunk/entity/edge/status linkage fields before audit at `tests/test_knowledge_integrity_consolidation_1589.py:108` through `tests/test_knowledge_integrity_consolidation_1589.py:127`. | PASS |
| AC-1c | `audit_integrity()` exposes the four audited categories in `serve/knowledge/src/owlbear_knowledge/integrity.py:11` through `serve/knowledge/src/owlbear_knowledge/integrity.py:84`. | The test calls `audit_integrity(conn)` after the linkage checks at `tests/test_knowledge_integrity_consolidation_1589.py:129` and asserts zero counts for all four categories at `tests/test_knowledge_integrity_consolidation_1589.py:131` through `tests/test_knowledge_integrity_consolidation_1589.py:134`. | PASS |
| AC-2 | `audit_integrity()` returns `chunks_orphaned`, `entities_orphaned`, `edges_dangling`, and `status_orphaned` in `serve/knowledge/src/owlbear_knowledge/integrity.py:16`, `serve/knowledge/src/owlbear_knowledge/integrity.py:29`, `serve/knowledge/src/owlbear_knowledge/integrity.py:42`, and `serve/knowledge/src/owlbear_knowledge/integrity.py:56`. | `tests/test_knowledge_integrity_consolidation_1589.py:144` disables FK enforcement, injects all four orphan categories, restores FK enforcement, then asserts exact counts plus injected-ID membership for all four categories at `tests/test_knowledge_integrity_consolidation_1589.py:173` through `tests/test_knowledge_integrity_consolidation_1589.py:182`. | PASS |

- Blocking findings: none.

## Observations
- Challenger returned `reconsider` on two theoretical false-green arguments. I overrode that with an explicit code-reader cross-check because, under the refined AC, both concerns are non-blocking: the document-content assertion at `tests/test_knowledge_integrity_consolidation_1589.py:90` distinguishes the known `store_chunks()` backfill behavior in `serve/knowledge/src/owlbear_knowledge/document_store.py:104`, and AC-1b requires proof of persisted linkage fields rather than intentionally wrong-input overwrite behavior.
- The earlier structural blockers are closed in the live file: AC-1 is again a single function at `tests/test_knowledge_integrity_consolidation_1589.py:52`, and the chunk existence check is by `chunk_ids[0]` at `tests/test_knowledge_integrity_consolidation_1589.py:94`.
- No independent quality-runner rerun was needed because builder evidence was internally consistent and the remaining review questions were resolvable from static proof inspection. `get_errors` also reported no file-level problems in `tests/test_knowledge_integrity_consolidation_1589.py`.

[[2026-05-17T02:37:44+02:00]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | No | N/A | Root `tests/` has no convention mapping target. Changed file: `tests/test_knowledge_integrity_consolidation_1589.py` only. No `serve/{pkg}/src/**` or interface changes. |
| 2 | External attribution | No | N/A | No external sources referenced. Test patterns sourced from sibling task #1586 (internal). |
| 3 | Research doc | No | N/A | No research artifact exists for this task. |
| 4 | Deletion detection | No | N/A | Builder merged `test_ac1b_chain_linkage_fields_are_set_before_audit` INTO `test_ac1_clean_chain_returns_zero_for_all_audit_categories` (in-file merge only). No file deletions; no orphaned references. |

### Verification Layers
- Layer 1 — grep: `serve/knowledge/README.md` contains no references to `integrity_consolidation`, `audit_integrity`, or `1589`; no removed symbols to check.
- Layer 2 — editorial: Test-only task; no documentation file was created or modified upstream. No README coherence impact. No-impact determination confirmed.

### Scratch Cleanup
- No `.owlbear/scratch/1589-*` files found.

[[2026-05-17T02:44:46+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 4631 passed, 253 failed (pytest), 2006 passed / 55 failed (vitest), ruff clean, eslint clean
- All failures pre-existing in unrelated files (test_cockpit_view.py, test_server.py, test_engine_accessor_migration.py, test_ideation_diagram.py, test_cockpit_pds_build_compat.py) — none touched by #1589 commits
- Task's own test file: 2 passed, 0 failed
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (only file changed: tests/test_knowledge_integrity_consolidation_1589.py — knowledge domain, test-only)
- purpose match: PASS (consolidation integration test exercising init_db + DocumentStore API chain + audit_integrity, matches task title and AC)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
AC required 4 refinement cycles to close false-green paths. Each cycle the reviewer caught legitimate gaps: (1) missing row-presence assertions, (2) missing linkage field assertions, (3) ambiguous \"same test\" language causing split proof, (4) document row not discriminated from store_chunks() backfill. Final AC is precise and well-structured. The number of cycles indicates the original specification was under-specified for a consolidation test — notable gaps requiring significant builder/reviewer rework.

### Commit Integrity
- upstream commit presence: PASS (f7cd800e — builder commit touches only tests/test_knowledge_integrity_consolidation_1589.py; 5 total commits across builder/test-writer cycles)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
- AC quality score 3/5: -.03
- No other deductions

### Confidence: 0.97
### Action: archive
