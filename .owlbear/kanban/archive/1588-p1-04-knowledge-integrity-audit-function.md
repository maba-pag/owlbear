---
id: 1588
title: 'P1-04: Knowledge integrity audit function'
status: archived
priority: needed
created: 2026-05-15T16:24:50.332910+00:00
updated: 2026-05-16T13:30:35.489608+00:00
tags:
  - phase-1
  - scope:knowledge
  - type:build
  - db-integrity
parent: 1580
depends_on:
  - 1587
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Parent: #1580

Scope:
- In scope: Extract `audit_integrity()` from `owlbear_knowledge.schema` into a new `owlbear_knowledge/integrity.py` module; export it as the canonical import path; maintain backward-compatible re-export from `schema.py`.
- Out of scope: Schema DDL changes (done in #1586), data mutation/repair, vector payload linkage, CLI entry point, behavioral changes to the audit queries.

Context:
The `audit_integrity()` function already exists in `serve/knowledge/src/owlbear_knowledge/schema.py` (implemented during #1587's builder phase). This task extracts it into a dedicated module for separation of concerns (DDL/migration logic vs audit logic). The function's behavior is fully covered by `tests/test_knowledge_integrity_audit_1587.py` (8 tests, all passing).

Acceptance Criteria:
AC-1: Module `owlbear_knowledge/integrity.py` exists and `from owlbear_knowledge.integrity import audit_integrity` resolves to a callable accepting `conn: sqlite3.Connection` and returning `dict[str, dict[str, int | list[str]]]` with keys `chunks_orphaned`, `entities_orphaned`, `edges_dangling`, `status_orphaned`.
AC-2: `audit_integrity()` detects orphan chunks (chunk.document_id not in documents), orphan entities (entity.document_id not in documents), dangling edges (edge.source_id or edge.target_id not in entities), and orphan document_status entries (document_status.document_id not in documents) using LEFT JOIN with IS NULL checks.
AC-3: `audit_integrity()` executes no INSERT, UPDATE, or DELETE statements; connection `total_changes` before and after the call is unchanged.
AC-4: `from owlbear_knowledge.schema import audit_integrity` remains importable (backward-compatible re-export preserving the archived #1587 test contract).

Builder Guidance:
- The function body is already implemented at `serve/knowledge/src/owlbear_knowledge/schema.py:527-601`. Move it to `integrity.py` and leave a one-line re-export in `schema.py`.
- The test-writer will create tests importing from `owlbear_knowledge.integrity` (natural RED state since the module does not exist yet).
- Existing tests in `tests/test_knowledge_integrity_audit_1587.py` import from `owlbear_knowledge.schema` — AC-4 requires they continue to pass via the re-export.
- Do NOT add `audit_integrity` to `owlbear_knowledge/__init__.py` — that is a separate public-API decision for the parent task.

Proof bundle: behavioral

[[2026-05-16T14:35:12+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single module extraction, one function |
| Interface clarity | PASS | AC-1 specifies exact signature, return type shape, and key names |
| Dependency correctness | PASS | #1587 archived/completed (dep_status ok); function implemented there |
| Module layering | PASS | `integrity.py` in same package, no upward imports |
| TDD compliance | PASS | Test-writer will write AC-1/AC-4 focused tests importing from `integrity.py` (natural RED: module doesn't exist) |
| KISS/YAGNI | PASS | Single module for audit logic; parent #1580 plans more integrity ops |
| Premise challenge | PASS | Function exists in `schema.py` but extraction justified: schema.py handles DDL+migrations, audit logic is distinct concern |
| Pattern consistency | PASS | Follows domain-specific module pattern (document_store.py, graph_store.py, etc.) |
| Security surface | N/A | Internal read-only function, no new system boundaries |
| Single domain | PASS | Knowledge module only |
| User-action detection | N/A | Counter-signals: AC defines function signature and importable module |

### Proof-Bundle Validation
- Planner assignment: behavioral (body only, frontmatter null)
- Frontmatter set: behavioral (fixed during REFINE)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single obvious approach (module extraction with re-export)

### Challenge Results
- Challenger: reconsider (confidence 0.35)
- Valid findings addressed:
  1. TDD contract drift → clarified in scope/context that function exists, test-writer creates RED via `integrity.py` import
  2. Missing compatibility contract → added AC-4 (re-export from schema.py)
  3. AC-2 ambiguity (LEFT JOIN / NOT IN) → reworded to \"LEFT JOIN with IS NULL checks\"
  4. proof_bundle frontmatter null → set to `behavioral`
  5. Remaining task value → justified: SRP extraction, growth direction for integrity domain
- Architect response: accepted all findings, applied REFINE

### REFINE Applied
- Rewrote scope to explicitly frame as module extraction (not greenfield)
- Added context section explaining existing implementation
- Clarified AC-2 query strategy (removed \"/ NOT IN\" ambiguity)
- Added AC-4 for backward-compatible re-export
- Added builder guidance with file locations and constraints
- Set proof_bundle frontmatter

### Verdict: APPROVED (after REFINE)
### Action: Refined body (scope, ACs, guidance), set proof_bundle frontmatter, advanced to todo.

[[2026-05-16T14:51:47+02:00]]
## Test-Writer Notes
- Test file: tests/test_knowledge_integrity_extraction_1588.py
- Classes: TestFromAC_IntegrityExtraction
- Tests per category: happy 8, edge 3, error 2, boundary 1
- Total: 14 tests, all FAIL (ModuleNotFoundError: No module named 'owlbear_knowledge.integrity')
- ruff: clean (reformatted by pre-commit hook before commit)
- AC coverage:
  | AC | Tests |
  |----|-------|
  | AC-1 (module importable, callable, return shape) | test_audit_integrity_is_callable, test_signature_accepts_sqlite3_connection, test_return_value_has_all_four_required_keys, test_return_value_inner_dicts_have_count_and_ids |
  | AC-2 (detection: orphan chunks, entities, edges, status) | test_clean_db_all_four_keys_count_zero_ids_empty, test_detects_orphan_chunk, test_detects_orphan_entity, test_detects_dangling_edge_orphan_source_id, test_detects_dangling_edge_orphan_target_id, test_detects_orphan_document_status, test_multiple_orphans_same_category_all_reported, test_multiple_orphan_categories_reported_independently, test_valid_edge_with_both_endpoints_not_flagged_as_dangling |
  | AC-3 (read-only, total_changes unchanged) | test_read_only_total_changes_unchanged_on_clean_db, test_read_only_total_changes_unchanged_with_orphans |
  | AC-4 (backward-compat re-export from schema.py) | test_schema_reexport_is_importable, test_schema_reexport_returns_same_structure |

[[2026-05-16T15:03:25+02:00]]
## Builder Notes
- Files changed:
  - serve/knowledge/src/owlbear_knowledge/integrity.py
  - serve/knowledge/src/owlbear_knowledge/schema.py
- Implementation summary:
  - Extracted `audit_integrity(conn)` from `schema.py` into new `integrity.py` module as canonical import path.
  - Preserved backward compatibility by re-exporting from `schema.py` via `from owlbear_knowledge.integrity import audit_integrity`.
  - Added `__all__ = ("audit_integrity", "init_db")` in `schema.py` so re-export is explicit/public.
- RED verification (quality-runner):
  - tests/test_knowledge_integrity_extraction_1588.py collection failed with `ModuleNotFoundError: owlbear_knowledge.integrity` before implementation.
- GREEN verification (quality-runner):
  - Scoped tests passed: 25 passed, 0 failed, 0 skipped.
  - Test files:
    - tests/test_knowledge_integrity_extraction_1588.py
    - tests/test_knowledge_integrity_audit_1587.py
  - Lint status: clean (ruff clean on touched source + task test file).
  - Coverage: runner did not emit explicit per-module percentage for `owlbear_knowledge.integrity` in summary; no coverage failures reported.
- Durable module-level test check:
  - No canonical module-level integrity test file found under `serve/knowledge/tests/` for this target; skipped per workflow guidance.
- Commit:
  - `b1bd1832206eb176a7e52d044578644e1c2d967d`
  - Message: `refactor: extract knowledge integrity audit module (#1588, builder)`
- AC mapping:
  - AC-1: `owlbear_knowledge/integrity.py` exists and exports callable `audit_integrity(conn)` with expected return shape/keys (validated by 1588 tests).
  - AC-2: Query behavior preserved exactly (LEFT JOIN + IS NULL checks for all four categories).
  - AC-3: Function remains read-only (total_changes unchanged tests passing).
  - AC-4: `from owlbear_knowledge.schema import audit_integrity` remains importable and behavior-consistent (1587 + 1588 compatibility tests passing).

[[2026-05-16T15:17:59+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1588 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: scoped quality proof reported 25 passed, 0 failed, 0 skipped across `tests/test_knowledge_integrity_extraction_1588.py` and `tests/test_knowledge_integrity_audit_1587.py`; lint clean; no coverage failures reported; IDE diagnostics clean on touched source and task test files.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/knowledge/src/owlbear_knowledge/integrity.py:11` defines `audit_integrity(conn: sqlite3.Connection) -> dict[str, dict[str, int | list[str]]]`; `serve/knowledge/src/owlbear_knowledge/integrity.py:70-84` returns the four required keys. | `tests/test_knowledge_integrity_extraction_1588.py:111`, `:115`, `:123`, `:130` exercise importability, callability, signature surface, and return-shape checks. | PASS |
| AC-2 | `serve/knowledge/src/owlbear_knowledge/integrity.py:20-24`, `:33-37`, `:46-51`, `:60-64` use LEFT JOIN + IS NULL detection for chunks, entities, edges, and status rows. | `tests/test_knowledge_integrity_extraction_1588.py:160`, `:175`, `:187`, `:200`, `:214`, `:228`, `:245`, `:265` plus archived compatibility coverage in `tests/test_knowledge_integrity_audit_1587.py:94`, `:110`, `:124`, `:137`, `:181`, `:196`. | PASS |
| AC-3 | `serve/knowledge/src/owlbear_knowledge/integrity.py:20-64` contains SELECT-only queries; no INSERT/UPDATE/DELETE statements present. | `tests/test_knowledge_integrity_extraction_1588.py:282`, `:290` and `tests/test_knowledge_integrity_audit_1587.py:164` verify `total_changes` is unchanged. | PASS |
| AC-4 | `serve/knowledge/src/owlbear_knowledge/schema.py:15-17` re-exports `audit_integrity` from the new module. | `tests/test_knowledge_integrity_extraction_1588.py:310`, `:316` and archived import path at `tests/test_knowledge_integrity_audit_1587.py:21`. | PASS |
- Challenger cross-check: no blocking findings; proceed recommendation (confidence 0.82).
- Blocking findings: none.

## Observations
- The test-writer body summary says "Total: 14 tests", but the live task test file contains 17 `test_` cases; together with the 8 archived tests this explains the builder's 25-pass total. This is a stale summary, not a proof defect.
- AC-1's type-annotation details are proved more strongly by code inspection than by runtime assertions; not blocking for this extraction task because the implemented signature matches the contract exactly.

[[2026-05-16T15:22:14+02:00]]
## Docs Gate

**Changed files:** `serve/knowledge/src/owlbear_knowledge/integrity.py` (new), `serve/knowledge/src/owlbear_knowledge/schema.py` (re-export added)

**Convention mapping:** `serve/knowledge/src/**` → `serve/knowledge/README.md`

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | PASS — no update needed | Layer 1: no grep hits for `audit_integrity` or `integrity` in README; no stale references to removed schema.py location. Layer 2: "Module groups" table lists public `__init__.py` exports only; `audit_integrity` is intentionally excluded from `__init__.py` per builder constraints (parent #1580 decision). No task-caused doc drift. |
| External Attribution | N/A | Pure code extraction refactor; no external sources. |
| Research Doc | N/A | No research artifact referenced in task body. |
| Deletion Detection | N/A | No files deleted; `audit_integrity` moved with backward-compatible re-export preserved in `schema.py` (L15–17). |

**Scratch cleanup:** 3 files removed (`1588-pytest-output.txt`, `1588-quality-check.txt`, `1588-ruff-output.txt`). Directory clean.

[[2026-05-16T15:30:35+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 4642 passed, ~240 failed, 9 errors, 14 skipped; lint clean
- All failures/errors pre-existing (baseline: 236–244 failed, 9 errors across recent runs #1595, #1632)
- No new regressions introduced by #1588
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (changed files: `integrity.py` new, `schema.py` modified — both in `serve/knowledge/src/owlbear_knowledge/`, knowledge domain only)
- purpose match: PASS (module extraction with backward-compatible re-export matches stated task purpose exactly)
- extraneous scope: none (builder commit touches exactly 2 files, both in target domain)
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC-1 through AC-4 are specific with exact paths, signatures, return types, and constraints. Challenger found 5 pre-REFINE gaps (TDD drift, missing compat AC, query ambiguity, null proof_bundle, task-value justification) — all addressed in REFINE. Minor gap: AC could have been right first time without challenger intervention.

### Commit Integrity
- upstream commit presence: PASS (`b1bd1832` builder, `43cb5686` test-writer — both present with correct format `#1588, {role}`)
- commit scope: PASS (builder commit: 2 files, 90 insertions / 78 deletions — purely knowledge domain)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
No deductions applied:
- Regression: PASS (0)
- Intent: PASS (0)
- Lint: clean (0)
- AC quality: 4/5 > 3 (0)
- Reviewer evidence: present and detailed (0)
- Evidence integrity: no concerns (0)

### Confidence: 1.00
### Action: archive
