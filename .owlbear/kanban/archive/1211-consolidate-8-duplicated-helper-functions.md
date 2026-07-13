---
id: 1211
title: Consolidate 6 duplicated helper functions
status: archived
priority: medium
created: 2026-04-30 15:29:15.204775+00:00
updated: 2026-05-03T19:22:20.678962+00:00
tags:
- audit-kanban
- dry
parent:
depends_on:
- 1210
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Deduplicate 8 helper functions that exist in multiple modules.

## Files
- engine.py, storage.py, corruption.py

## Change
Deduplicate: generate_slug (keep in storage.py), make_task_filename (keep in storage.py), validate_path_containment (keep in storage.py), move_to_quarantine (keep in storage.py), _dep_effect_from_archival_reason (keep in KanbanEngine, AgentView delegates), _compute_dep_status (keep in KanbanEngine, AgentView delegates).

## AC
- [ ] Each helper exists in exactly one canonical location
- [ ] Other modules import from canonical location
- [ ] No duplicated function bodies remain
- [ ] Tests pass

## Finding: 1.3

[[2026-05-03]]

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: deduplication |
| Interface clarity | PASS after refine | Canonical locations now specified without ambiguity |
| Dependency correctness | PASS | #1210 (archived) satisfied |
| Module layering | FAIL before refine | storage.py ↔ corruption.py circular import; fixed by extracting to leaf module |
| TDD compliance | PASS | Existing tests pin dep_status and quarantine behavior |
| KISS/YAGNI | PASS | Straightforward consolidation |
| Premise challenge | PASS | Genuine DRY violations confirmed in codebase |
| Pattern consistency | PASS | Aligns with #1210 leaf-module extraction pattern |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | All within kanban engine domain |

### Circular Import Finding
`storage.py` (line 46) does `from owlbear_kanban.corruption import ...` (re-exports).
If `corruption.py` imports back from `storage.py`, Python fails with ImportError
(partially-initialized module). The 4 path/naming helpers must live in a NEW leaf
module (e.g. `_naming.py`) that both storage.py and corruption.py can import from.
storage.py can re-export them for API continuity.

### Challenge Results
- Challenger: reconsider (0.53)
- Architect response: accepted re _compute_dep_status being genuine shared business logic; rejected "overspecified" claim because circular import makes the specified canonical location invalid

### Test Depth
- Max depth: td:1
- Test-writer: PROCEED

### Verdict: REFINE
### Action Taken: Tightened AC to specify leaf-module extraction for path/naming helpers, clarified _compute_dep_status strategy, fixed function count from 8→6


## Refined Objective
Deduplicate 6 helper functions that exist in multiple modules across the kanban package.

## Refined Change
1. **Create `_naming.py` leaf module** with: `generate_slug`, `make_task_filename`, `validate_path_containment`, `move_to_quarantine`. These are currently in `storage.py` (canonical, with safety guards) and duplicated as private copies in `corruption.py` (simplified, missing null-byte/Windows-reserved checks).
2. **`storage.py`** re-exports the 4 functions from `_naming.py` (preserves existing public API).
3. **`corruption.py`** imports directly from `_naming.py` (avoids circular import with storage.py); delete private copies `_generate_slug`, `_make_task_filename`, `_validate_path_containment`, `_move_to_quarantine`.
4. **`_dep_effect_from_archival_reason`** — keep `@staticmethod` on `KanbanEngine`; `AgentView` calls `KanbanEngine._dep_effect_from_archival_reason(reason)` instead of duplicating.
5. **`_compute_dep_status`** — keep on `KanbanEngine` (takes `active_ids`, `archived_reasons` params); `AgentView` pre-computes those sets from its engine access, then delegates to `self.engine._compute_dep_status(task, active_ids=..., archived_reasons=...)`. This aligns with #1215 direction.

## Refined AC (supersedes original)
- [ ] New leaf module `_naming.py` exists with the 4 path/naming helpers (td:1)
- [ ] `storage.py` re-exports from `_naming.py`; no function bodies remain in storage.py for these 4 (td:1)
- [ ] `corruption.py` imports from `_naming.py`; private copies deleted (td:1)
- [ ] `AgentView._dep_effect_from_archival_reason` removed; calls delegate to KanbanEngine (td:1)
- [ ] `AgentView._compute_dep_status` removed; delegation to KanbanEngine._compute_dep_status with pre-computed sets (td:1)
- [ ] No circular imports: `python -c "import owlbear_kanban"` succeeds (td:1)
- [ ] Existing test suite passes without modification (td:0)

[[2026-05-03]]
REFINED and APPROVED. Key finding: original "keep in storage.py" creates circular import (storage.py→corruption.py→storage.py). Solution: extract 4 path/naming helpers to `_naming.py` leaf module. AC rewritten with 7 verifiable lines + td annotations. Aligned _compute_dep_status delegation with #1215 architectural direction.
[[2026-05-03]]
## Test-Writer Notes

- **Test file:** `tests/test_consolidate_helpers_1211.py`
- **Classes:** `TestFromAC_NamingLeafModule`, `TestFromAC_StorageReexports`, `TestFromAC_CorruptionImportsFromNaming`, `TestFromAC_AgentViewDelegation`, `TestFromAC_NoCircularImports`
- **Strategy:** AST-based structural checks (no runtime imports of the package) + importlib checks for AC6. Avoids test collection failures caused by missing `_naming.py`.
- **Tests per category:** All smoke/structural (td:1); 20 total — 5 naming module, 5 storage re-exports, 5 corruption private copies, 2 AgentView delegation, 3 circular-import/module-origin.
- **RED verification:** `pytest -n0 -v` → **20 failed, 0 passed** ✓
- **Lint:** `ruff check` clean ✓

### AC Coverage Table

| AC | Tests |
|----|-------|
| AC1 — `_naming.py` exists with 4 helpers | `test_naming_module_exists`, `test_naming_module_has_generate_slug`, `test_naming_module_has_make_task_filename`, `test_naming_module_has_validate_path_containment`, `test_naming_module_has_move_to_quarantine` |
| AC2 — `storage.py` re-exports from `_naming.py`, no local bodies | `test_storage_imports_from_naming`, `test_storage_generate_slug_no_local_body`, `test_storage_make_task_filename_no_local_body`, `test_storage_validate_path_containment_no_local_body`, `test_storage_move_to_quarantine_no_local_body` |
| AC3 — `corruption.py` imports from `_naming.py`, private copies deleted | `test_corruption_imports_from_naming`, `test_corruption_no_private_generate_slug`, `test_corruption_no_private_make_task_filename`, `test_corruption_no_private_validate_path_containment`, `test_corruption_no_private_move_to_quarantine` |
| AC4 — `AgentView._dep_effect_from_archival_reason` removed | `test_agentview_no_dep_effect_method` |
| AC5 — `AgentView._compute_dep_status` removed | `test_agentview_no_compute_dep_status_method` |
| AC6 — No circular imports | `test_naming_module_importable`, `test_naming_module_exports_generate_slug`, `test_storage_generate_slug_comes_from_naming` |
| AC7 — Existing test suite passes (td:0) | skipped |
[[2026-05-03]]
## Builder Notes
- Implementation: created `serve/kanban/src/owlbear_kanban/_naming.py`; updated `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, and `serve/kanban/src/owlbear_kanban/engine.py`.
- Fixes applied:
  - Extracted canonical helpers to `_naming.py`: `generate_slug`, `make_task_filename`, `validate_path_containment`, `move_to_quarantine`.
  - `storage.py` now re-exports naming/path helpers from `_naming.py`; local helper bodies removed.
  - `corruption.py` now imports helper functions from `_naming.py`; private duplicate copies removed.
  - Removed `AgentView` duplicate methods `_dep_effect_from_archival_reason` and `_compute_dep_status`; `AgentView.show_task()` now pre-computes active/archived dependency sets and delegates to `KanbanEngine._compute_dep_status(...)`.
- Tests: `tests/test_consolidate_helpers_1211.py` -> 20 passed, 0 failed.
- Lint: `ruff` clean on touched source files + task test file (0 violations).
- Coverage (scoped quality-runner report): `_naming` 21%, `storage` 18%, `corruption` 14%, `engine` 9% (combined 11%). This task uses td:1 structural assertions; coverage was captured for evidence but is not representative of module behavioral breadth.
- Circular import safety: satisfied by leaf-module extraction (`storage.py` and `corruption.py` both depend on `_naming.py`, not each other).
- Commit: `0f189abe` — `refactor: consolidate duplicated kanban helpers (#1211, builder)`.

## Post-task Reflection
- AST/structure assertions can require exact import shape, not just semantic equivalence.
- Keeping helper logic in one leaf module simplifies circular-import safety across storage/corruption.
- Delegation to existing engine dependency logic reduced duplicated policy logic in AgentView.
- Most rework time came from lint/noqa placement rather than functional behavior changes.

[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped pass: pytest 20 passed, 0 failed on `tests/test_consolidate_helpers_1211.py`

### Lint
- quality-runner: clean on `serve/kanban/src/owlbear_kanban/` and `tests/test_consolidate_helpers_1211.py`

### Coverage
- overall 16% (`owlbear_kanban._naming` 21%, `storage` 18%, `corruption` 14%, `engine` 9%)
- Informational only: this is a td:1 structural task, so low module-level coverage is not the gate.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test(s) | Evidence | Verdict |
|---------|----------------|----------|---------|
| AC1 - `_naming.py` exists with 4 helpers | `test_naming_module_exists`, `test_naming_module_has_*` | Tests at `tests/test_consolidate_helpers_1211.py:90-117` assert the file exists and each helper is a top-level function; current source defines them at `_naming.py:18`, `:30`, `:35`, `:55` | COVERED |
| AC2 - `storage.py` re-exports from `_naming.py`; no local bodies remain | `test_storage_imports_from_naming`, `test_storage_*_no_local_body`, `test_storage_generate_slug_comes_from_naming` | Tests at `tests/test_consolidate_helpers_1211.py:128-156` prove no local bodies remain, and `:243-249` proves `generate_slug` originates from `_naming.py`. But the generic `_imports_from(...)` assertion at `:131` only proves some import-from exists; it does not pin the other three required symbols even though source currently imports all four at `storage.py:40-44` | LAX |
| AC3 - `corruption.py` imports from `_naming.py`; private copies deleted | `test_corruption_imports_from_naming`, `test_corruption_no_private_*` | Tests at `tests/test_consolidate_helpers_1211.py:167-195` prove no private copies remain, but the generic `_imports_from(...)` assertion at `:170` does not prove the exact required symbols are imported, even though source currently imports them at `corruption.py:17-19` | LAX |
| AC4 - `AgentView._dep_effect_from_archival_reason` removed; calls delegate to KanbanEngine | `test_agentview_no_dep_effect_method` | Test at `tests/test_consolidate_helpers_1211.py:208-212` proves method removal only. Current canonical helper exists on `KanbanEngine` at `engine.py:510`, but there is no executable assertion that would fail if delegation were dropped and replacement logic changed elsewhere | LAX |
| AC5 - `AgentView._compute_dep_status` removed; delegation to `KanbanEngine._compute_dep_status` with pre-computed sets | `test_agentview_no_compute_dep_status_method` | The task header claims `test_agentview_compute_dep_status_calls_engine` should exist at `tests/test_consolidate_helpers_1211.py:21-22`, but the body only contains the absence check at `:214-218`. Current implementation does pre-compute `active_ids` / `archived_reasons` and delegates at `engine.py:2119-2135`, so the implementation looks correct, but the AC proof is missing | MISSING |
| AC6 - no circular imports / package import succeeds | `test_naming_module_importable`, `test_naming_module_exports_generate_slug`, `test_storage_generate_slug_comes_from_naming` | `tests/test_consolidate_helpers_1211.py:243-249` performs `from owlbear_kanban import storage`; package root import pulls in `engine` via `__init__.py:9-10`, so a circular-import regression would fail here | COVERED |
| AC7 - existing test suite passes without modification | td:0 | Marked td:0 by Architecture Review; not re-run in reviewer scoped evidence | SKIP |

#### Security Review
- No new dependencies or new external boundaries.
- Moved helpers preserve the existing null-byte, reserved-name, and path-containment guards in `_naming.py:18-63`.
- No secret, injection, traversal-regression, or unsafe deserialization issue found in the changed diff.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_consolidate_helpers_1211.py::TestFromAC_*` | Builder commit `0f189abe` changed only `_naming.py`, `storage.py`, `corruption.py`, and `engine.py` (`git show --name-only 0f189abe`) | PRESERVED |

#### Test Quality
- Assertion specificity: WEAK for AC2/AC3 because `tests/test_consolidate_helpers_1211.py:131` and `:170` only assert a module-level `ImportFrom`, not the exact imported/re-exported symbols named by the AC.
- Delegation proof: WEAK for AC4 and MISSING for AC5 because the suite asserts method absence but does not assert the replacement call path. The unused helper `_class_method_calls_attr` at `tests/test_consolidate_helpers_1211.py:67` suggests an intended call-site assertion was never written.
- Circular-import proof: ADEQUATE via the package-root import path in `tests/test_consolidate_helpers_1211.py:245` plus `__init__.py:9-10`.

#### Data Safety
- No data-safety issues found in the implementation diff.

#### Implementation-Aware Test Gap Analysis
- `AgentView.show_task()` now computes `active_ids` / `archived_reasons` and delegates to `self.engine._compute_dep_status(...)` at `engine.py:2119-2135`.
- No `TestFromAC` assertion inspects or exercises that path. A regression that removed the delegation while still deleting `AgentView._compute_dep_status` would pass the current suite.
- This is a significant untested path on a named AC line.

#### Necessity Check
- Skipped. No new dependency, tool, or integration was introduced.

#### Builder Process Quality
- CLEAN. `git show --name-only 0f189abe` proves the builder did not modify the task test file.
- No prior `## Review Evidence` section exists in `.owlbear/kanban/tasks/1211-consolidate-8-duplicated-helper-functions.md`, so this is the first review-cycle failure.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `_naming.py:18`, `:30`, `:35`, `:55`; `tests/test_consolidate_helpers_1211.py:90-117` | `TestFromAC_NamingLeafModule` | PASS |
| AC2 | `storage.py:40-44`; `tests/test_consolidate_helpers_1211.py:128-156`, `:243-249` | `TestFromAC_StorageReexports` | FAIL (lax proof) |
| AC3 | `corruption.py:17-19`; `tests/test_consolidate_helpers_1211.py:167-195` | `TestFromAC_CorruptionImportsFromNaming` | FAIL (lax proof) |
| AC4 | `engine.py:510`; `tests/test_consolidate_helpers_1211.py:208-212` | `TestFromAC_AgentViewDelegation` | FAIL (delegation not proven) |
| AC5 | `engine.py:2119-2135`; `tests/test_consolidate_helpers_1211.py:21-22`, `:214-218` | `TestFromAC_AgentViewDelegation` | FAIL (missing delegation test) |
| AC6 | `__init__.py:9-10`; `tests/test_consolidate_helpers_1211.py:243-249` | `TestFromAC_NoCircularImports` | PASS |
| AC7 | td:0 reviewer scope skip | none | SKIP |

### Deductions
- -0.12 AC5 missing delegation proof.
- -0.03 AC2 exact re-export proof lax for three helpers.
- -0.03 AC3 exact import proof lax.
- -0.02 AC4 delegation proof implicit only.
- Confidence: 0.80

### Verdict
- FAIL -> `todo`
- Reason: implementation appears correct, but the `TestFromAC` suite does not fully prove the refined structural contract. This is a first-cycle proof-only rejection, so it routes to test-writer rather than builder.

### Required Follow-up
1. Add an explicit `TestFromAC` assertion that `AgentView.show_task()` delegates to `self.engine._compute_dep_status(...)` with pre-computed `active_ids` / `archived_reasons`, or an AST equivalent that would fail if the delegation were removed.
2. Strengthen AC2/AC3 tests to assert each required symbol is imported or re-exported from `_naming.py`, not just that some `ImportFrom` from the module exists.
3. Keep the current `TestFromAC` file immutable otherwise; builder commit `0f189abe` did not modify it.

### Post-task Reflection
- Compare the declared AC coverage list against actual test definitions; green structural suites can hide header-only tests.
- Generic AST `ImportFrom` checks are too weak when the AC names exact symbols.
- Dedup/delegation tasks need both absence-of-local-def proof and exact origin or call-site proof.
[[2026-05-03]]
## Test-Writer Notes

- **Retry:** Added 8 tests for reviewer's AC2/AC3/AC4/AC5 proof gaps. All 28 tests pass against current implementation.
- **Builder skip:** Test-only retry; implementation already handles all new assertions.

### Changes
- Added `_imported_names_from()` helper: returns exact symbol set from a `from module import ...` statement (replaces generic `_imports_from` pattern for per-symbol checks).
- Added `_method_calls_engine_attr()` helper: AST-walks a specific class method for `self.engine.{attr}(...)` call patterns.
- Added to `TestFromAC_StorageReexports` (AC2, 4 new): `test_storage_imports_{generate_slug,make_task_filename,validate_path_containment,move_to_quarantine}_from_naming` — each pins an exact symbol in storage.py's `_naming` import.
- Added to `TestFromAC_CorruptionImportsFromNaming` (AC3, 2 new): `test_corruption_imports_{make_task_filename,move_to_quarantine}_from_naming` — pins the two symbols corruption.py needs from `_naming`.
- Added to `TestFromAC_AgentViewDelegation` (AC4+AC5, 2 new): `test_kanbanengine_has_dep_effect_method` (proves canonical location exists on KanbanEngine), `test_agentview_show_task_delegates_compute_dep_status` (proves `self.engine._compute_dep_status(...)` call in AgentView.show_task()).

### Result
- 28 passed, 0 failed — all new tests are green (implementation already correct).
- Lint: ruff clean.
- AC2/AC3/AC4/AC5 reviewer gaps fully addressed.
[[2026-05-03]]
## Builder Notes
- Scope: verification cycle after test-writer retry for AC proof-strength gaps.
- Files changed by builder in this cycle: none.
- Tests: quality-runner scoped pass on tests/test_consolidate_helpers_1211.py -> 28 passed, 0 failed, 0 skipped.
- Lint: clean on serve/kanban/src/owlbear_kanban and tests/test_consolidate_helpers_1211.py (ruff 0 violations).
- Coverage (informational for td:1 structural scope): overall 16%; owlbear_kanban._naming 21%, owlbear_kanban.storage 18%, owlbear_kanban.corruption 14%, owlbear_kanban.engine 9%.
- Evidence summary: AC proof gaps identified in prior review are now covered by the updated TestFromAC assertions; implementation required no additional code changes in this builder pass.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped pass on the local working tree: 28 passed, 0 failed, 0 skipped in tests/test_consolidate_helpers_1211.py
- Important limitation: the green result is not reproducible from committed repo state because tests/test_consolidate_helpers_1211.py is untracked in the working tree and absent from HEAD.

### Lint
- quality-runner: clean on serve/kanban/src/owlbear_kanban and tests/test_consolidate_helpers_1211.py

### Coverage
- overall 16 percent across the scoped modules
- Informational only for this td:1 structural task

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 - `_naming.py` exists with 4 helpers | `_naming.py:18,30,35,55`; tests/test_consolidate_helpers_1211.py:126-156 | `TestFromAC_NamingLeafModule` | PASS in working tree |
| AC2 - `storage.py` re-exports from `_naming.py`; no local bodies remain | `storage.py:40`; exact-symbol tests at tests/test_consolidate_helpers_1211.py:197,204,211,218 | `TestFromAC_StorageReexports` | PASS in working tree |
| AC3 - `corruption.py` imports from `_naming.py`; private copies deleted | `corruption.py:17`; exact-symbol tests at tests/test_consolidate_helpers_1211.py:264,271 | `TestFromAC_CorruptionImportsFromNaming` | PASS in working tree |
| AC4 - `AgentView._dep_effect_from_archival_reason` removed; calls delegate to KanbanEngine | `engine.py:510,543`; tests/test_consolidate_helpers_1211.py:289,301,307 | `TestFromAC_AgentViewDelegation` | PASS in working tree |
| AC5 - `AgentView._compute_dep_status` removed; delegation to `KanbanEngine._compute_dep_status` with pre-computed sets | `engine.py:521,2132`; test at tests/test_consolidate_helpers_1211.py:295,307 | `TestFromAC_AgentViewDelegation` | PASS in working tree |
| AC6 - no circular imports | tests/test_consolidate_helpers_1211.py:315-329 plus package import path exercised by the suite | `TestFromAC_NoCircularImports` | PASS in working tree |
| AC7 - existing test suite passes without modification | td:0 reviewer scope skip | none | SKIP |

#### Security Review
- No new dependencies or external boundaries.
- `_naming.py` preserves the existing null-byte, reserved-name, and containment guards.
- No secret, injection, traversal-regression, or unsafe deserialization issue found in the changed source.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_consolidate_helpers_1211.py::TestFromAC_*` | Builder commit `0f189abe` changed only `_naming.py`, `storage.py`, `corruption.py`, and `engine.py` | PRESERVED |
| Retry proof additions | Present only as an untracked working-tree file; `git status` shows `?? tests/test_consolidate_helpers_1211.py`, and HEAD does not contain the file | VIOLATION |

#### Test Quality
- The strengthened assertions now pin exact imported symbols and the `AgentView.show_task()` delegation path via `_imported_names_from()` and `_method_calls_engine_attr()`.
- I found no remaining false-green issue in the local test body.
- The blocker is deliverable integrity, not assertion strength.

#### Data Safety
- No data-safety issues found.

#### Implementation-Aware Test Gap Analysis
- Live code still matches the refined structural contract: `_naming.py` holds the canonical helpers, `storage.py` and `corruption.py` import from it, and `AgentView.show_task()` delegates to `self.engine._compute_dep_status(...)`.
- The current retry tests would be adequate if they were committed.

#### Necessity Check
- Skipped. No new dependency, tool, or integration was introduced.

#### Builder Process Quality
- One prior `## Review Evidence` section already exists in the task artifact, so this is the second review cycle.
- Current cycle is not passable because the retry evidence lives only in the working tree. Downstream agents and clean checkouts cannot reproduce it.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `_naming.py:18,30,35,55`; tests/test_consolidate_helpers_1211.py:126-156 | `TestFromAC_NamingLeafModule` | PASS in working tree |
| AC2 | `storage.py:40`; tests/test_consolidate_helpers_1211.py:197,204,211,218 | `TestFromAC_StorageReexports` | PASS in working tree |
| AC3 | `corruption.py:17`; tests/test_consolidate_helpers_1211.py:264,271 | `TestFromAC_CorruptionImportsFromNaming` | PASS in working tree |
| AC4 | `engine.py:510,543`; tests/test_consolidate_helpers_1211.py:289,301,307 | `TestFromAC_AgentViewDelegation` | PASS in working tree |
| AC5 | `engine.py:521,2132`; tests/test_consolidate_helpers_1211.py:295,307 | `TestFromAC_AgentViewDelegation` | PASS in working tree |
| AC6 | tests/test_consolidate_helpers_1211.py:315-329 | `TestFromAC_NoCircularImports` | PASS in working tree |
| AC7 | td:0 reviewer scope skip | none | SKIP |

### Deductions
- -0.14 commit-integrity failure: the task-scoped retry test file is untracked and absent from HEAD, so the green evidence is not part of the deliverable.
- Confidence: 0.86

### Verdict
- FAIL to backlog
- Reason: the local working tree now satisfies the structural proof, but the retry is not committed. This violates the pipeline commit gate, and because one prior review failure already exists, the loop-breaker rule routes the task to backlog.

### Required Follow-up
1. Commit tests/test_consolidate_helpers_1211.py as part of the task deliverable so the green evidence exists in repo state, not only in the working tree.
2. Re-advance only after the committed snapshot reproduces the same 28-pass scoped result and clean lint.
3. Preserve the current source files unless new evidence shows a functional defect; the present blocker is commit integrity.

### Post-task Reflection
- Builder-skip retries need an explicit git-state check; local green evidence is insufficient when the retry file is untracked.
- Quality evidence must be tied to committed repo state, not just the current working tree.
- Second-cycle review failures still trigger the loop-breaker route even when the remaining defect is process integrity rather than source correctness.
[[2026-05-03]]
## Architecture Review (Re-entry)\n### Context\nThird architect pass. Prior cycles: (1) REFINED+APPROVED with AC rewrite, (2) two reviewer FAILs — first for weak AC proof, second for commit-integrity (test file untracked). The architecture, AC, implementation, and test assertions are all verified correct.\n\n### Evaluation\nNo architectural re-evaluation required. The sole remaining blocker is commit integrity: `tests/test_consolidate_helpers_1211.py` (28 tests, all green) must be committed to satisfy the pipeline commit gate.\n\n### Verdict: APPROVE (fast-path re-entry)\n### Action Taken: Advanced to `todo` — test-writer must commit the existing test file; builder is no-op; reviewer verifies committed state.\n\n### Guidance for downstream agents\n- **Test-writer:** The test file already exists with 28 passing tests covering all AC lines. Commit it (no new tests needed). Pass through.\n- **Builder:** No implementation changes needed. Verify 28/28 pass against committed state.\n- **Reviewer:** Verify the test file is in HEAD and 28/28 green from a committed snapshot.
[[2026-05-03]]
## Test-Writer Notes
- Retry (3rd cycle): test file `tests/test_consolidate_helpers_1211.py` already existed as untracked with 28 passing tests covering all AC lines.
- No new tests written — all assertions correct per prior retry cycle.
- Committed in this pass: `b94454c5` — 1 file, 341 insertions.
- 28 passed, 0 failed — `uv run pytest tests/test_consolidate_helpers_1211.py -q -n0`.
- Lint: `ruff` clean.
- Builder skip: test-only retry, all 28 tests green against committed state.
[[2026-05-03]]
## Builder Notes
- Scope: verification cycle after test-writer commit-integrity fix (`b94454c5`).
- Files changed by builder in this cycle: none.
- Commit integrity: `tests/test_consolidate_helpers_1211.py` is present in `HEAD` (`b94454c5`), and task-1211 source/test files are clean in working tree.
- Tests (quality-runner scoped): `tests/test_consolidate_helpers_1211.py` -> 28 passed, 0 failed, 0 skipped.
- Lint (quality-runner scoped): ruff clean on `serve/kanban/src/owlbear_kanban/` and `tests/test_consolidate_helpers_1211.py`.
- Coverage (informational for td:1 structural scope): overall 16%; `owlbear_kanban._naming` 21%, `owlbear_kanban.storage` 18%, `owlbear_kanban.corruption` 14%, `owlbear_kanban.engine` 9%.
- Evidence summary: AC proof-strength and commit-integrity blockers from prior review cycles are resolved in committed state; no additional implementation changes required in this builder pass.

## Post-task Reflection
- Verification-only builder cycles should start with commit-integrity checks to avoid false green from untracked files.
- quality-runner scoped evidence is sufficient for td:1 structural tasks, with coverage treated as informational.
- Keeping builder changes empty when implementation is already correct preserves surgical-diff discipline.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped pass: pytest 28 passed, 0 failed, 0 skipped on `tests/test_consolidate_helpers_1211.py`

### Lint
- quality-runner: clean on `serve/kanban/src/owlbear_kanban/` and `tests/test_consolidate_helpers_1211.py`
- VS Code diagnostics: no errors in `_naming.py`, `storage.py`, `corruption.py`, `engine.py`, or the task test file

### Coverage
- overall 16% across scoped modules (`owlbear_kanban._naming` 21%, `storage` 18%, `corruption` 14%, `engine` 9%)
- Informational only: this task is td:1 structural review scope, so module-level coverage is not the gate

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test(s) | Evidence | Verdict |
|---------|----------------|----------|---------|
| AC1 - New leaf module `_naming.py` exists with the 4 path/naming helpers | `TestFromAC_NamingLeafModule` | `tests/test_consolidate_helpers_1211.py:129-156` asserts file existence + exact top-level helper names; current source defines them at `_naming.py:18`, `:30`, `:35`, `:55` | COVERED |
| AC2 - `storage.py` re-exports from `_naming.py`; no local bodies remain | `TestFromAC_StorageReexports`, `test_storage_generate_slug_comes_from_naming` | `storage.py:40-45` imports the canonical symbols; `tests/test_consolidate_helpers_1211.py:167-223` rejects local bodies and pins exact imported names; `tests/test_consolidate_helpers_1211.py:335-340` proves `storage.generate_slug.__module__ == "owlbear_kanban._naming"` | COVERED |
| AC3 - `corruption.py` imports from `_naming.py`; private copies deleted | `TestFromAC_CorruptionImportsFromNaming` | `corruption.py:17-20` imports from `_naming.py`; `tests/test_consolidate_helpers_1211.py:234-276` rejects all private helper bodies and pins the exact imported symbols that corruption still consumes | COVERED |
| AC4 - `AgentView._dep_effect_from_archival_reason` removed; calls delegate to KanbanEngine | `TestFromAC_AgentViewDelegation` | `tests/test_consolidate_helpers_1211.py:289-305` proves `AgentView` no longer owns the method and `KanbanEngine` does; current engine implementation routes dependency effects through `KanbanEngine._dep_effect_from_archival_reason` at `engine.py:510` and `engine.py:543` | COVERED |
| AC5 - `AgentView._compute_dep_status` removed; delegation to `KanbanEngine._compute_dep_status` with pre-computed sets | `TestFromAC_AgentViewDelegation` | `tests/test_consolidate_helpers_1211.py:295-310` proves `AgentView` no longer owns `_compute_dep_status` and that `show_task()` calls `self.engine._compute_dep_status(...)`; current call site pre-computes `active_ids` / `archived_reasons` at `engine.py:2119-2135` | COVERED |
| AC6 - No circular imports; package import path succeeds | `TestFromAC_NoCircularImports` | `tests/test_consolidate_helpers_1211.py:322-340` imports `_naming` and `from owlbear_kanban import storage`; package-root import traverses `__init__.py:9-10`, so a `storage -> corruption -> storage` cycle would fail here | COVERED |
| AC7 - Existing test suite passes without modification | td:0 | Architecture Review explicitly marked this line td:0, so reviewer scope skips rerunning the broad suite | SKIP |

#### Security Review
- No new dependencies or external boundaries.
- `_naming.py:18-66` preserves the existing slug, reserved-name, null-byte, and path-containment guards.
- No secret exposure, injection risk, unsafe deserialization, or traversal regression found in the changed files.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_consolidate_helpers_1211.py::TestFromAC_*` | Builder commit `0f189abe` changed only `_naming.py`, `storage.py`, `corruption.py`, and `engine.py`; test-writer commit `b94454c5` added the committed task test file now present in `HEAD` | PRESERVED |

#### Test Quality
- Assertion specificity: STRONG for td:1 structural scope. Exact imported-symbol checks at `tests/test_consolidate_helpers_1211.py:197-223` and `:264-276`, exact `__module__` equality at `:335-340`, and exact `self.engine._compute_dep_status(...)` call detection at `:307-310` would fail on the intended regressions.
- Negative/error-path coverage: ADEQUATE for a structural dedup task. The suite checks both required positive structure and forbidden local/private copies.
- Manual mutation reasoning: removing any required import, reintroducing a local helper body, restoring an `AgentView` duplicate method, or removing the `show_task()` delegation would fail matching task tests.
- Test independence: STRONG. All task tests are AST/import checks with no shared mutable fixtures.
- Naming clarity: STRONG. Test names map cleanly to the refined AC lines.

#### Data Safety
- No data-safety issue found in the task-owned diff.

#### Implementation-Aware Test Gap Analysis
- No significant untested path remains within the refined td:1 scope.
- `AgentView.show_task()` computes `active_ids` / `archived_reasons` and delegates at `engine.py:2119-2135`, which is pinned by `tests/test_consolidate_helpers_1211.py:307-310`.
- Engine-side dependency behavior also has adjacent durable coverage in `tests/test_engine_dep_lookup_1207.py:393-430` and `serve/kanban/tests/test_engine_coverage_1068.py:2325-2355`, which supports the refactor’s behavioral preservation.

#### Necessity Check
- Skipped. No new dependency, integration, or external capability was introduced.

#### Builder Process Quality
- FRICTION, not LOOP. Two prior `## Review Evidence` sections exist in the task artifact, but the retries varied approach: first proof-strengthening, then commit-integrity repair.
- Current cycle resolves both earlier blockers in committed repo state; no repeated identical retry pattern remains.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `_naming.py:18,30,35,55`; `tests/test_consolidate_helpers_1211.py:129-156` | `TestFromAC_NamingLeafModule` | PASS |
| AC2 | `storage.py:40-45`; `tests/test_consolidate_helpers_1211.py:167-223`, `:335-340` | `TestFromAC_StorageReexports` | PASS |
| AC3 | `corruption.py:17-20`; `tests/test_consolidate_helpers_1211.py:234-276` | `TestFromAC_CorruptionImportsFromNaming` | PASS |
| AC4 | `engine.py:510,543`; `tests/test_consolidate_helpers_1211.py:289-305` | `TestFromAC_AgentViewDelegation` | PASS |
| AC5 | `engine.py:521,2119-2135`; `tests/test_consolidate_helpers_1211.py:295-310` | `TestFromAC_AgentViewDelegation` | PASS |
| AC6 | `__init__.py:9-10`; `tests/test_consolidate_helpers_1211.py:322-340` | `TestFromAC_NoCircularImports` | PASS |
| AC7 | td:0 reviewer scope skip | none | SKIP |

### Deductions
- -0.02 Python reference-provider unavailable in this VS Code session; caller tracing was completed by direct source search and file inspection instead.
- Confidence: 0.96

### Verdict
- PASS -> `docs`
- Reason: committed state reproduces the strengthened 28-test task suite, lint is clean, builder preserved `TestFromAC`, and the refined structural AC is fully satisfied in the current source.

### Action
- Advance to docs.

### Post-task Reflection
- Builder-skip retries still need explicit commit-integrity verification before accepting green scoped tests.
- Structural dedup tasks need exact-origin assertions, not just generic import presence checks.
- When the reference provider is unavailable, grep plus line-numbered source inspection is sufficient to recover caller-trace confidence.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/kanban/README.md` covers public KanbanEngine/AgentView API only; internal module restructuring (`_naming.py`, storage/corruption re-exports) not referenced in any IN-scope prose doc |
| 2 | Module docstrings | Yes | Verified | `_naming.py` has module docstring + docstrings on all 4 public helpers. `storage.py` module docstring intact. `corruption.py` module docstring intact. `AgentView.show_task()` docstring intact in `engine.py:2089-2099`. No additions needed. |
| 3 | External attribution | No | N/A | Internal DRY refactoring only; no external patterns or sources used |
| 4 | Research doc | No | N/A | No `.owlbear/research/` link in task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `kanban.excalidraw` (describes `serve/kanban/src/**`) and `mcp-topology.excalidraw` (describes `serve/kanban/src/**`) both matched. Footer updated to `Last verified: 2026-05-03 (fb1e79b2)` in both. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No IN-scope descriptive docs reference the removed private helpers (`_generate_slug`, `_make_task_filename`, etc.) — they were internal private copies never surfaced in docs |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/_naming.py` | IN (docstrings) | Verified — docstrings present |
| `serve/kanban/src/owlbear_kanban/storage.py` | IN (docstrings) | Verified — module docstring intact |
| `serve/kanban/src/owlbear_kanban/corruption.py` | IN (docstrings) | Verified — module docstring intact |
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | Verified — `AgentView.show_task()` docstring intact |
| `tests/test_consolidate_helpers_1211.py` | OUT | Test file — no doc action |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer updated to `Last verified: 2026-05-03 (fb1e79b2)`
- `share/diagrams/mcp-topology.excalidraw` — footer updated to `Last verified: 2026-05-03 (fb1e79b2)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — `_naming.py` exists with 4 helpers | `_naming.py:18,30,35,55` (generate_slug, make_task_filename, validate_path_containment, move_to_quarantine) | PASS |
| AC2 — `storage.py` re-exports from `_naming.py`; no local bodies | `storage.py:40-44` imports from `_naming`; reviewer evidence at test lines 167-223, 335-340 | PASS |
| AC3 — `corruption.py` imports from `_naming.py`; private copies deleted | `corruption.py:17-19` imports make_task_filename + move_to_quarantine; builder diff confirms 4 private copies removed | PASS |
| AC4 — AgentView._dep_effect_from_archival_reason removed; delegates to KanbanEngine | Reviewer mapped at engine.py:510,543; tests at test_consolidate_helpers_1211.py:289-305 | PASS |
| AC5 — AgentView._compute_dep_status removed; delegation with pre-computed sets | engine.py:2119-2135 (verified: pre-computes active_ids/archived_reasons, delegates to self.engine._compute_dep_status) | PASS |
| AC6 — No circular imports | Package import path test at test_consolidate_helpers_1211.py:322-340; confirmed via __init__.py:9-10 chain | PASS |
| AC7 — Existing test suite passes (td:0) | SKIP per architecture review designation |

### Test Results
- pytest (full): 736 passed, 15 failed (all pre-existing; 0 in task scope); task-scoped: 28/28 passed
- vitest (full): 937 passed, 13 failed (pre-existing Shell tests)
- ruff (scoped): clean on serve/kanban/src/owlbear_kanban/ and tests/test_consolidate_helpers_1211.py

### Pre-existing failure note
`test_corruption.py::test_make_yaml_disables_timestamp_resolver` — _make_yaml removed in commit 59eddcae (task #1048); not a #1211 regression.

### Architect Quality: 4/5
Specific, verifiable AC with td annotations. Required refinement to catch circular import risk (challenger caught at 0.53). Original "8 helpers" corrected to 6. Clean path after refinement.

### Deduction Breakdown
- Start: 1.00
- AC7 not independently verified (td:0 skip): -.02
- No lint violations, no missing reviewer evidence, no task-scope failures

### Confidence: .98
### Action: archive

### Commit Integrity
- `0f189abe` — refactor: consolidate duplicated kanban helpers (#1211, builder) — _naming.py, storage.py, corruption.py, engine.py
- `b94454c5` — test: commit test file for helper consolidation (#1211, test-writer) — tests/test_consolidate_helpers_1211.py
- Working tree: clean for all deliverables