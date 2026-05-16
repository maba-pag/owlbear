---
id: 1587
title: 'P1-03: Tests — knowledge integrity audit function'
status: archived
priority: needed
created: 2026-05-15T16:24:36.952846+00:00
updated: 2026-05-16T12:12:19.544743+00:00
tags:
  - phase-1
  - scope:knowledge
  - type:test
  - db-integrity
parent: 1580
depends_on:
  - 1586
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Parent: #1580

Scope:
- In scope: Failing tests for a read-only integrity audit function that detects orphan rows across knowledge tables.
- Out of scope: Schema constraint changes, vector payload checks, data mutation/repair.

Acceptance Criteria:
AC-1: Test calls `audit_integrity(conn)` on a database containing one orphan chunk row (parent document deleted via direct SQL with FK disabled); asserts result[`chunks_orphaned`] is a dict with `count` == `1` and `ids` containing the orphan chunk ID.
AC-2: Test calls `audit_integrity(conn)` on a database containing one edge with `source_id` referencing a non-existent entity (inserted via direct SQL with FK disabled); asserts result[`edges_dangling`] is a dict with `count` == `1` and `ids` containing the dangling edge ID.
AC-3: Test calls `audit_integrity(conn)` on a database containing one entity row whose `document_id` references a non-existent document (inserted via direct SQL with FK disabled); asserts result[`entities_orphaned`] is a dict with `count` == `1` and `ids` containing the orphan entity ID.
AC-4: Test calls `audit_integrity(conn)` on a database containing one `document_status` row whose `document_id` references a non-existent document (inserted via direct SQL); asserts result[`status_orphaned`] is a dict with `count` == `1` and `ids` containing the orphan document_id.
AC-5: Test calls `audit_integrity(conn)` on a clean database with a source→document→chunk→entity→edge→document_status chain; asserts result contains keys `chunks_orphaned`, `entities_orphaned`, `edges_dangling`, `status_orphaned`, each a dict with `count` == `0` and `ids` == `[]`.
AC-6: Test calls `audit_integrity(conn)` on a database containing at least one orphan row, captures `conn.total_changes` before and after the call, and asserts the values are equal (function is read-only).

Proof bundle: behavioral

[[2026-05-16T09:05:02+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One function under test (`audit_integrity`), one domain |
| Interface clarity | PASS | AC specifies function signature, input preconditions, output dict shape per category |
| Dependency correctness | PASS | #1586 archived/completed; schema at v13 with NOT NULL enforcement |
| Module layering | PASS | Tests in root `tests/`, function in `serve/knowledge/` — standard pattern |
| TDD compliance | PASS | This IS the RED phase task; #1588 is the GREEN implementation |
| KISS/YAGNI | PASS | 6 focused test scenarios, no abstractions |
| Premise challenge | PASS | No existing audit function; parent #1580 AC-2 requires it |
| Pattern consistency | PASS | Follows existing knowledge test patterns (conn fixture, direct SQL for orphan injection) |
| Security surface | N/A | Internal read-only audit, no new system boundaries |
| Single domain | PASS | Knowledge module only |
| User-action detection | N/A | Counter-signals: AC defines function signature and test outcomes; tagged `type:test` |

### Proof-Bundle Validation
- Planner assignment: behavioral (body)
- Frontmatter set: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (type:test pass-through — builder writes test code)

### REFINE Applied
Original 3 ACs had structural gaps identified during review and confirmed by challenger:
1. **Missing categories**: Only 2 of 4 detection categories had individual violation tests (chunks_orphaned, edges_dangling). Added AC-3 (entities_orphaned) and AC-4 (status_orphaned).
2. **Payload shape ambiguity**: Original said "value `1` and the orphan ID in the detail list" — ambiguous dict structure. Aligned with #1588 contract: per-category dict with `count` and `ids` keys.
3. **Non-mutation untested**: Parent #1580 requires "without mutating data." Added AC-6 verifying `conn.total_changes` unchanged.
4. **Zero-path underspecified**: Original AC-3 said "reports zero violations" without shape. Rewritten as AC-5 requiring each category key present with `count` == 0 and `ids` == [].

### Challenge Results
- Challenger: block (confidence 0.34)
- Valid findings addressed:
  1. Sibling-contract drift (target_id untested) → noted for test-writer; consolidation test #1589 covers gap
  2. Untested non-mutation → added AC-6
  3. Payload shape ambiguity → rewrote all ACs with explicit `count`/`ids` structure
  4. Weak zero-path assertions → tightened AC-5 with shape verification
- Architect response: accepted all structural findings, applied REFINE. Target_id variant not added as separate AC — test-writer may add it as supplementary test.
- Consolidation-test gap: NONE (#1589 exists)

### Builder Guidance
- Import path: `from owlbear_knowledge.schema import audit_integrity` (function does not exist yet — RED phase)
- Test fixture: use `@pytest.fixture() def conn()` pattern with in-memory DB + `init_db(conn)` (matches existing knowledge tests)
- Orphan injection: disable FK with `PRAGMA foreign_keys = OFF`, insert orphan row, re-enable FK, then call `audit_integrity`
- The test-writer should consider adding a supplementary test for `edges_dangling` via `target_id` (not in AC but strengthens coverage)

### Verdict: APPROVED (after REFINE)
### Action: Refined ACs from 3→6, set proof_bundle frontmatter, advanced to todo.

[[2026-05-16T09:15:06+02:00]]
## Test-Writer Notes
- Test file: tests/test_knowledge_integrity_audit_1587.py
- Classes: TestFromAC_IntegrityAudit
- Tests per category: happy 1, edge 4, error 1, boundary 1
- Total: 7 tests, all FAIL (ImportError — `audit_integrity` not yet in schema.py)
- ruff: clean

AC coverage:
| AC   | Test method |
|------|-------------|
| AC-1 | test_chunks_orphaned_detects_one_orphan |
| AC-2 | test_edges_dangling_detects_orphan_source_id |
| AC-3 | test_entities_orphaned_detects_one_orphan |
| AC-4 | test_status_orphaned_detects_one_orphan |
| AC-5 | test_clean_db_returns_all_keys_with_zero_counts |
| AC-6 | test_audit_is_read_only |
| Supp | test_edges_dangling_detects_orphan_target_id |

Failure mode: ImportError on all 7 tests (collection fails; `audit_integrity` not exported from `owlbear_knowledge.schema`).
Builder import path: `from owlbear_knowledge.schema import audit_integrity`

[[2026-05-16T09:42:55+02:00]]
## Builder Notes

### Files Changed
- serve/knowledge/src/owlbear_knowledge/schema.py

### Implementation Summary
- Added `audit_integrity(conn)` to `owlbear_knowledge.schema`.
- Function performs read-only SELECT audits for:
  - `chunks_orphaned`
  - `entities_orphaned`
  - `edges_dangling` (both orphan `source_id` and orphan `target_id`)
  - `status_orphaned`
- Return contract matches AC/test expectations per category:
  - `{ "count": int, "ids": list[str] }`

### RED Verification (pre-implementation)
- quality-runner scoped on `tests/test_knowledge_integrity_audit_1587.py`
- Result: collection ImportError for missing `audit_integrity`; 7 `TestFromAC_IntegrityAudit` tests blocked at import (expected RED)
- Lint: clean

### GREEN Verification (task-scoped)
- quality-runner scoped:
  - `tests/test_knowledge_integrity_audit_1587.py`
  - lint paths: `serve/knowledge/src/owlbear_knowledge/schema.py`, `tests/test_knowledge_integrity_audit_1587.py`
  - coverage module: `owlbear_knowledge.schema`
- Result: **7 passed, 0 failed, 0 skipped**
- Lint: **clean**
- Coverage (`owlbear_knowledge.schema`): **44%** on task-only test file

### Expanded Coverage Evidence
- quality-runner scoped with schema-focused existing tests:
  - `tests/test_knowledge_integrity_audit_1587.py`
  - `tests/test_schema_constraint_enforcement_1586.py`
  - `tests/test_knowledge_schema_constraints_1585.py`
  - `tests/test_schema_bookmark_drop_1583.py`
  - `tests/test_enrichment_schema.py`
- Result: **71 passed, 0 failed**
- Lint: **clean**
- Coverage (`owlbear_knowledge.schema`): **73%**

### Module-Level Durable Check
- quality-runner scoped on `serve/knowledge/tests/test_graph_store_counts.py`
- Result: unchanged pre-existing fixture/setup errors (`edges.document_id` NOT NULL constraint in `populated_graph` setup), not introduced by this change
- Lint: clean

### Commit
- `a06fc0462d526cfd59789446a28cf9a15a8a1707`
- Message: `feat: add integrity audit query function (#1587, builder)`

### Evidence Summary
- AC behavior implemented and validated by task tests (all passing).
- Function is read-only (SELECT-only implementation; AC-6 test passes).
- No lint issues in changed source or task test file.
- Additional schema-focused suite confirms compatibility for related schema paths.

[[2026-05-16T10:06:01+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1587 -> todo | AC-5 proof is insufficient because the clean-path test never exercises a valid non-null `edges.target_id`, so target-side dangling-edge regressions can false-green.
- Builder evidence reviewed first: task packet reported `7 passed / 0 failed / 0 skipped`, lint clean, and coverage `44%` task-only / `73%` expanded; commit `a06fc0462d526cfd59789446a28cf9a15a8a1707` is present in `.git/logs`; editor diagnostics are clean for `serve/knowledge/src/owlbear_knowledge/schema.py` and `tests/test_knowledge_integrity_audit_1587.py`.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/knowledge/src/owlbear_knowledge/schema.py:536`, `serve/knowledge/src/owlbear_knowledge/schema.py:586` | `tests/test_knowledge_integrity_audit_1587.py:94` | PASS |
| AC-2 | `serve/knowledge/src/owlbear_knowledge/schema.py:562`, `serve/knowledge/src/owlbear_knowledge/schema.py:565-566`, `serve/knowledge/src/owlbear_knowledge/schema.py:594` | `tests/test_knowledge_integrity_audit_1587.py:110`, supplementary target-missing proof at `tests/test_knowledge_integrity_audit_1587.py:181` | FAIL |
| AC-3 | `serve/knowledge/src/owlbear_knowledge/schema.py:549`, `serve/knowledge/src/owlbear_knowledge/schema.py:590` | `tests/test_knowledge_integrity_audit_1587.py:124` | PASS |
| AC-4 | `serve/knowledge/src/owlbear_knowledge/schema.py:576`, `serve/knowledge/src/owlbear_knowledge/schema.py:598` | `tests/test_knowledge_integrity_audit_1587.py:137` | PASS |
| AC-5 | `serve/knowledge/src/owlbear_knowledge/schema.py:586`, `serve/knowledge/src/owlbear_knowledge/schema.py:590`, `serve/knowledge/src/owlbear_knowledge/schema.py:594`, `serve/knowledge/src/owlbear_knowledge/schema.py:598` | clean zero-path test seeds `target_id=None` at `tests/test_knowledge_integrity_audit_1587.py:154` and only checks zero-shape at `tests/test_knowledge_integrity_audit_1587.py:160` | FAIL |
| AC-6 | `serve/knowledge/src/owlbear_knowledge/schema.py:527-601` | `tests/test_knowledge_integrity_audit_1587.py:175`, `tests/test_knowledge_integrity_audit_1587.py:177`, `tests/test_knowledge_integrity_audit_1587.py:179` | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-5 / proof sufficiency for edge handling | The clean-path proof never exercises a valid non-null `edges.target_id`; the only non-null target case in the suite is intentionally broken. A regression that falsely flags any non-null target reference as dangling would still pass this task. | `tests/test_knowledge_integrity_audit_1587.py:154`, `tests/test_knowledge_integrity_audit_1587.py:181`, `tests/test_knowledge_integrity_audit_1587.py:188`, `tests/test_knowledge_integrity_audit_1587.py:193`; `serve/knowledge/src/owlbear_knowledge/schema.py:565-566`; AC-5 in `.owlbear/kanban/tasks/1587-p1-03-tests-knowledge-integrity-audit-function.md:34` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen the clean-path proof so at least one zero-result case seeds an edge with both valid `source_id` and valid non-null `target_id`, then assert `edges_dangling` remains empty. | `tests/test_knowledge_integrity_audit_1587.py` | Blocking finding #1 |

## Observations
- The required challenger pass returned `reconsider` and pointed to the same target-side false-green risk; I agree with that finding and used it as the routing blocker.
- I did not run an independent `quality-runner` rerun because the builder packet was internally consistent and the blocker is visible from the committed test assertions themselves.
- Separate non-routing observation: this task's import guidance still points at `owlbear_knowledge.schema` in `.owlbear/kanban/tasks/1587-p1-03-tests-knowledge-integrity-audit-function.md:81` and `.owlbear/kanban/tasks/1587-p1-03-tests-knowledge-integrity-audit-function.md:109`, while sibling task `#1588` still defines the public surface as `owlbear_knowledge.integrity` in `.owlbear/kanban/tasks/1588-p1-04-knowledge-integrity-audit-function.md:25` and `.owlbear/kanban/tasks/1588-p1-04-knowledge-integrity-audit-function.md:29`. I am not using that mismatch as the routing blocker for `#1587`, but it should be reconciled before `#1588` leaves backlog.

[[2026-05-16T10:13:19+02:00]]
## Test-Writer Notes
- Retry: added 1 test for reviewer gap (valid non-null target_id not flagged as dangling).
- Builder skip: test-only retry, all 8 tests green against current impl.

**New test:** `test_edge_with_valid_nonnull_target_id_not_flagged_as_dangling`
- Seeds `entity-src` and `entity-tgt` (both existing), inserts edge with `source_id=entity-src` and `target_id=entity-tgt`
- Asserts `edges_dangling["count"] == 0` and `edges_dangling["ids"] == []`
- Guards against target-side false-positive regression (reviewer blocking finding #1)

**Quality-runner evidence:** 8 passed, 0 failed, lint clean — `8b5a4c13`
**AC coverage:** unchanged (AC-5 gap plugged by supplementary proof test)

[[2026-05-16T10:27:59+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1587 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: original builder packet reported task tests `7 passed / 0 failed / 0 skipped`, lint clean, and coverage `44%` task-only / `73%` expanded; test-writer retry packet reported `8 passed / 0 failed`, lint clean.
- Independent verification performed via direct file inspection of the live source/tests plus the required challenger pass (`proceed`, confidence `0.84`); no contradictions found.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/knowledge/src/owlbear_knowledge/schema.py:532`, `serve/knowledge/src/owlbear_knowledge/schema.py:586` | `tests/test_knowledge_integrity_audit_1587.py:94` | PASS |
| AC-2 | `serve/knowledge/src/owlbear_knowledge/schema.py:558`, `serve/knowledge/src/owlbear_knowledge/schema.py:564`, `serve/knowledge/src/owlbear_knowledge/schema.py:565`, `serve/knowledge/src/owlbear_knowledge/schema.py:594` | `tests/test_knowledge_integrity_audit_1587.py:110`, `tests/test_knowledge_integrity_audit_1587.py:181` | PASS |
| AC-3 | `serve/knowledge/src/owlbear_knowledge/schema.py:545`, `serve/knowledge/src/owlbear_knowledge/schema.py:590` | `tests/test_knowledge_integrity_audit_1587.py:124` | PASS |
| AC-4 | `serve/knowledge/src/owlbear_knowledge/schema.py:572`, `serve/knowledge/src/owlbear_knowledge/schema.py:598` | `tests/test_knowledge_integrity_audit_1587.py:137` | PASS |
| AC-5 | `serve/knowledge/src/owlbear_knowledge/schema.py:586`, `serve/knowledge/src/owlbear_knowledge/schema.py:590`, `serve/knowledge/src/owlbear_knowledge/schema.py:594`, `serve/knowledge/src/owlbear_knowledge/schema.py:598` | `tests/test_knowledge_integrity_audit_1587.py:148`, `tests/test_knowledge_integrity_audit_1587.py:161`, `tests/test_knowledge_integrity_audit_1587.py:196`, `tests/test_knowledge_integrity_audit_1587.py:208`, `tests/test_knowledge_integrity_audit_1587.py:211` | PASS |
| AC-6 | `serve/knowledge/src/owlbear_knowledge/schema.py:527`, `serve/knowledge/src/owlbear_knowledge/schema.py:532`, `serve/knowledge/src/owlbear_knowledge/schema.py:545`, `serve/knowledge/src/owlbear_knowledge/schema.py:558`, `serve/knowledge/src/owlbear_knowledge/schema.py:572` | `tests/test_knowledge_integrity_audit_1587.py:164`, `tests/test_knowledge_integrity_audit_1587.py:175`, `tests/test_knowledge_integrity_audit_1587.py:177` | PASS |

- Blocking findings: none.

## Observations
- The prior false-green on valid non-null `edges.target_id` handling is now closed by the added negative-proof test at `tests/test_knowledge_integrity_audit_1587.py:196`, `tests/test_knowledge_integrity_audit_1587.py:208`, and `tests/test_knowledge_integrity_audit_1587.py:211` against the implementation's explicit source/target joins at `serve/knowledge/src/owlbear_knowledge/schema.py:564` and `serve/knowledge/src/owlbear_knowledge/schema.py:565`.
- Challenger cross-check returned `proceed` and found no remaining blocking proof gap. The only note was a minor AC-5 literalism point around the task text saying `source→document→...`; I treated that as non-blocking because `audit_integrity()` audits chunk/entity/edge/status orphaning and the retry now proves both positive and negative edge-target behavior.
- I did not run an independent `quality-runner` rerun because the upstream evidence was internally consistent, diagnostics for the live source/test files are clean, and the original blocker was resolved directly in the committed test assertions.

[[2026-05-16T10:38:19+02:00]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A | `serve/knowledge/README.md` mapped via convention. `audit_integrity` added to `schema.py` only; not re-exported from `owlbear_knowledge/__init__.py` (grep confirms 0 hits in `__init__.py`). Internal utility, not a public API surface. Module groups table in README covers public exports only — no drift. |
| 2 | External attribution | No | N/A | No external sources referenced in builder/test-writer notes. |
| 3 | Research doc | No | N/A | No research artifact for this task. |
| 4 | Deletion detection | No | N/A | No files deleted. |

### Verification Layers
- Layer 1 — grep: `audit_integrity` not present in `serve/knowledge/src/owlbear_knowledge/__init__.py`; no removed symbols/flags/commands in README target.
- Layer 2 — editorial: `serve/knowledge/README.md` accurately describes public API surface; addition of internal `audit_integrity` does not affect any documented section.

### Scratch Cleanup
No `.owlbear/scratch/1587-*` files found.

[[2026-05-16T14:12:19+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 4629 passed, 236 failed, 14 skipped; lint has 4 pre-existing hard-tab violations in `share/skills/w-task-decomposition/SKILL.md`
- All 236 failures are in unrelated domains (cockpit view, engine accessor migration, MCP server, ideation diagram) with zero causal path to the knowledge `schema.py` change — pre-existing background debt
- regression verdict: PASS (no task-caused regressions)

### Intent Verification
- scope alignment: PASS (3 commits touch only `serve/knowledge/src/owlbear_knowledge/schema.py` and `tests/test_knowledge_integrity_audit_1587.py`)
- purpose match: PASS (added integrity audit function + tests matching stated task scope)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
Original 3 ACs had notable structural gaps (only 2/4 detection categories, ambiguous dict shape, untested non-mutation, underspecified zero-path). Architect identified all via challenger challenge (block, 0.34) and applied REFINE expanding to 6 precise ACs with explicit `count`/`ids` contract. Final ACs are specific and verifiable. Score reflects initial draft quality offset by excellent catch-and-correct discipline.

### Commit Integrity
- upstream commit presence: PASS (`0ff9bf9b` test-writer, `a06fc046` builder, `8b5a4c13` test-writer retry — all verified via `git log`)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive"
