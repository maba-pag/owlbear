---
id: 1350
title: Remove legacy dispatch export and refresh kanban docs
status: archived
priority: medium
created: 2026-05-04T18:27:23.261100+00:00
updated: 2026-05-05T12:59:42.160638+00:00
tags:
- sync-blocker
- kanban
- docs
- api-contract
parent:
depends_on:
- 1342
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

`pick_dispatchable()` is deprecated in favor of `AgentView.pick_tasks()`, but it is still exported from `owlbear_kanban.__all__` and protected by tests. The package README also contains stale raw-engine examples that no longer match current signatures. Because `serve/kanban/README.md` is consumer-facing and synced to main, the package should not ship with broken examples or protected legacy API drift.

Audit decision: remove or explicitly quarantine the deprecated dispatch API and refresh the package README before sync.

## Acceptance Criteria

1. Audit first-party imports and real callers of `pick_dispatchable()`.
2. If no active first-party caller requires it, remove `pick_dispatchable` from `owlbear_kanban.__all__` and root-package exports.
3. If a temporary compatibility path is still required, keep it only behind an explicit deprecation/quarantine decision and update tests to assert that limited contract.
4. Update or remove tests that currently require `pick_dispatchable` to remain in `__all__` as a normal public export.
5. Refresh `serve/kanban/README.md` examples so they match current `KanbanEngine` and `AgentView` signatures.
6. Remove the stale `pick_dispatchable(tasks)` README example or replace it with `AgentView.pick_tasks()` usage.
7. Ensure README mutation examples do not advertise nonexistent raw-engine parameters such as `tags=` on `edit_task`.
8. Run package export tests and documentation/API smoke tests after the change.

## Key Files

- `serve/kanban/src/owlbear_kanban/__init__.py`
- `serve/kanban/src/owlbear_kanban/dispatch.py`
- `serve/kanban/README.md`
- `tests/test_init_exports_1213.py`
- `tests/test_dispatch_gate_port_1214.py`
- `tests/test_cockpit_boundary.py`

## Audit Evidence

- `pick_dispatchable()` emits `DeprecationWarning`, but root package exports still include it.
- `tests/test_init_exports_1213.py` still enforces the deprecated root export.
- `serve/kanban/README.md` documents `pick_dispatchable(tasks)` even though the implementation takes a `KanbanEngine`.
- `serve/kanban/README.md` shows raw engine edit examples that do not match the current `edit_task` signature.

## Source

Deployment audit finding group 7, 2026-05-04.

[[2026-05-05]]

## Architecture Review

**Verdict:** APPROVED (with AC refinement)

### AC Assessment

| Original AC | Assessment | Action |
|---|---|---|
| AC1 (audit callers) | Already done — evidence in task body. Not a testable AC. | Removed — converted to precondition note |
| AC2 (remove from __all__) | Verifiable, precise | Kept, made specific (td:1) |
| AC3 (compatibility path) | Dead path — no caller exists. Conditional never fires. | Removed |
| AC4 (update tests) | Verifiable but vague | Refined: specific test + negative assertion (td:1) |
| AC5 (refresh README) | Vague — "match current signatures" | Split into specific line fixes (td:0) |
| AC6 (remove stale example) | Verifiable | Merged into AC about README section removal (td:0) |
| AC7 (fix mutation examples) | Verifiable, specific | Kept with exact fix specified (td:0) |
| AC8 (run tests) | Process step, not AC | Removed (implied by pipeline) |

### Refined Acceptance Criteria

1. Remove `pick_dispatchable` from the import line and from `__all__` in `serve/kanban/src/owlbear_kanban/__init__.py`; update module docstring to remove "dispatch selector (pick_dispatchable)" mention. (td:1)
2. In `tests/test_init_exports_1213.py`: remove `test_pick_dispatchable_in_dunder_all`; remove `"pick_dispatchable"` from the `existing` set in `test_dunder_all_new_additions_are_exactly_five_symbols`; add negative assertion `assert "pick_dispatchable" not in owlbear_kanban.__all__`. (td:1)
3. In `serve/kanban/README.md`: remove the entire "Dispatch helper" subsection (deprecated note + code example showing `pick_dispatchable(tasks)`). (td:0)
4. In `serve/kanban/README.md`: replace `engine.edit_task(42, tags=["phase-1"])` with `engine.edit_task("42", add_tags=["phase-1"])` in the Launch/Usage code block. (td:0)
5. Run `uv run doc-index` to regenerate `.owlbear/doc-index.md` after README changes. (td:0)
6. `dispatch.py` module and `pick_dispatchable` function body are NOT deleted — they remain importable via `from owlbear_kanban.dispatch import pick_dispatchable` for the deprecation-path tests in `test_dispatch_gate_port_1214.py`. (td:0)

### Architecture Notes

- **Single domain**: kanban package API contract — ✓
- **Single responsibility**: public-surface cleanup (export + docs) — ✓ (tightly coupled changes)
- **Dependency direction**: no new dependencies, no upward imports — ✓
- **Pattern consistency**: follows existing deprecation→removal pattern
- **No security surface change**

### Dependency Analysis

- depends_on: [#1342] — archived (satisfied) ✓
- `dispatch.py` rank constants (`PRIORITY_RANK`, `STATUS_RANK`) imported by `engine.py` and `agent_view.py` — module stays intact
- `test_dispatch_gate_port_1214.py` imports directly from `owlbear_kanban.dispatch` — unaffected by root removal

### Challenger Result

Challenger returned `reconsider` (0.67). Concerns addressed:
- Public API removal: project policy "no legacy, no backwards compat"; function is deprecated with working successor
- Negative assertion gap: added to refined AC2
- doc-index drift: added AC5
- Override: justified by project principles + all concerns resolved in refinement

### Preconditions (from audit evidence)

- No first-party production caller of `pick_dispatchable` exists (grep across serve/cockpit, serve/mcp-kanban, serve/knowledge, serve/browser: zero hits)
- Function already emits DeprecationWarning at call-time
- `AgentView.pick_tasks()` is the shipped successor with full test coverage

[[2026-05-05]]
Architecture review complete. AC refined from 8 vague/conditional lines to 6 precise, test-depth-annotated lines. Challenger override justified. Test-writer: AC1-2 are td:1, rest td:0.
[[2026-05-05]]
## Test-Writer Notes

**Test file:** `tests/test_init_exports_1350.py`

**Classes:**
- `TestFromAC_DispatchExportRemoval` — AC1 contract tests
- `TestFromAC_TestFileSurgery` — AC2 structural tests

**Tests per category:**

| Category | Count |
|---|---|
| Happy path (contract) | 2 |
| Structural (file inspection) | 2 |
| **Total** | **4** |

**Fail confirmation:** 4 collected, 4 FAILED, 0 passed. Lint: ruff clean.

**AC coverage:**

| AC | Tests | Status |
|---|---|---|
| AC1: remove from `__all__` + import, update docstring | `test_pick_dispatchable_absent_from_dunder_all`, `test_module_docstring_no_longer_advertises_pick_dispatchable` | ✅ covered |
| AC2: remove positive test, add negative assertion to `test_init_exports_1213.py` | `test_positive_pick_dispatchable_test_removed`, `test_negative_assertion_present` | ✅ covered |
| AC3-6: td:0 — no tests | — | ✅ pass-through |

**Builder notes:**
- `dispatch.py` and `pick_dispatchable` function body must NOT be deleted (AC6). `test_dispatch_gate_port_1214.py` imports directly from `owlbear_kanban.dispatch` — unaffected by root removal.
- `test_init_exports_1213.py` also has `test_pick_dispatchable_importable_from_root` which will fail after the root import is removed — builder should handle that too.
[[2026-05-05]]
## Builder Notes
- Implementation: removed root-package `pick_dispatchable` export/import and docstring mention in `serve/kanban/src/owlbear_kanban/__init__.py`; updated export-contract tests in `tests/test_init_exports_1213.py`; refreshed `serve/kanban/README.md` examples by removing deprecated Dispatch helper subsection and correcting `edit_task` call signature; regenerated `.owlbear/doc-index.md` via `uv run doc-index`.
- Tests: 48 passed, 0 failed (scoped quality run across `tests/test_init_exports_1350.py`, `tests/test_init_exports_1213.py`, `tests/test_dispatch_gate_port_1214.py`).
- Coverage: 100% on touched module `owlbear_kanban.__init__`.
- ruff: clean on `serve/kanban/src/owlbear_kanban/__init__.py`, `tests/test_init_exports_1213.py`, `tests/test_init_exports_1350.py`.
- Evidence summary: RED confirmed pre-change with all 4 `TestFromAC_*` tests failing in `tests/test_init_exports_1350.py`; post-change GREEN verified with quality-runner and no regressions in module-level export/deprecation-path tests.
- Fixes applied: removed legacy root export contract while preserving direct import path `from owlbear_kanban.dispatch import pick_dispatchable` (no changes to `dispatch.py`).

### Post-task Reflection
- Problem faced: legacy export expectations were split across both task-scoped and older module-level tests; direct symbol removal required synchronized updates.
- Workaround applied: ran scoped quality checks including both task-scoped and module-level regression files to avoid false-green.
- Pattern discovered: deprecation-path compatibility can be preserved cleanly by removing only root re-export while retaining module-level symbol.
- Time sink: README drift required doc-index regeneration to keep canonical docs index in sync.
- Quality gap addressed: added explicit negative assertion in durable export tests to prevent accidental reintroduction of deprecated root exports.
[[2026-05-05]]
## Review Evidence

### Test Results
- Quality-runner scoped pass: 68 passed, 0 failed, 0 skipped across `tests/test_init_exports_1350.py`, `tests/test_init_exports_1213.py`, `tests/test_dispatch_gate_port_1214.py`, and `tests/test_cockpit_boundary.py`.
- Included `tests/test_cockpit_boundary.py` as an adjacent regression because a root-package export change can hide outside a task-local green suite.

### Lint Results
- Ruff clean on `serve/kanban/src/owlbear_kanban/__init__.py`, `tests/test_init_exports_1213.py`, `tests/test_init_exports_1350.py`, `tests/test_dispatch_gate_port_1214.py`, and `tests/test_cockpit_boundary.py`.

### Coverage
- `owlbear_kanban.__init__`: 100% statement coverage.
- Overall 31% from the scoped run is not the gate for this narrow diff-scoped review.

### Test-Writer Audit
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 remove import line/root export, remove from `__all__`, update docstring | `tests/test_init_exports_1350.py::TestFromAC_DispatchExportRemoval::test_pick_dispatchable_absent_from_dunder_all`; `tests/test_init_exports_1350.py::TestFromAC_DispatchExportRemoval::test_module_docstring_no_longer_advertises_pick_dispatchable` | No for the root-namespace/import-line portion. A build that keeps `pick_dispatchable` bound on the package root but removes it from `__all__` still passes these tests. | MISSING |
| AC2 remove positive durable test, prune `existing` set, add negative assertion | `tests/test_init_exports_1350.py::TestFromAC_TestFileSurgery::test_positive_pick_dispatchable_test_removed`; `tests/test_init_exports_1350.py::TestFromAC_TestFileSurgery::test_negative_assertion_present` | No for the `existing`-set cleanup. The task tests prove deletion of one positive test and presence of one negative assertion, but not that `tests/test_init_exports_1213.py` stopped treating `pick_dispatchable` as a legacy baseline symbol. | MISSING |
| AC3 remove Dispatch helper subsection | No tests required (td:0); README has no `Dispatch helper` or `pick_dispatchable(tasks)` matches and now flows from Launch / Usage to methods and AgentView sections. | PASS |
| AC4 use `engine.edit_task("42", add_tags=["phase-1"])` | No tests required (td:0); exact README line is present. | PASS |
| AC5 regenerate `.owlbear/doc-index.md` | No tests required (td:0); doc-index entry for `serve/kanban/README.md` mirrors current README headings. | PASS |
| AC6 keep `dispatch.py` and `pick_dispatchable` importable via module path | Covered by durable regression: `tests/test_dispatch_gate_port_1214.py` imports the direct module path and the scoped run stayed green; `dispatch.py` still defines `pick_dispatchable`. | PASS |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | `serve/kanban/src/owlbear_kanban/__init__.py:9,10,17,19`; `tests/test_init_exports_1350.py:20,24`; no executable root-namespace absence test found in `tests/` | `test_pick_dispatchable_absent_from_dunder_all`; `test_module_docstring_no_longer_advertises_pick_dispatchable` | FAIL |
| AC2 | `tests/test_init_exports_1213.py:50,52,68`; `tests/test_init_exports_1350.py:33,39`; no task test asserts the `existing`-set cleanup directly | `test_positive_pick_dispatchable_test_removed`; `test_negative_assertion_present` | FAIL |
| AC3 | `serve/kanban/README.md:9,31,52` plus no `Dispatch helper` or `pick_dispatchable(tasks)` matches in that file | td:0 | PASS |
| AC4 | `serve/kanban/README.md:26` | td:0 | PASS |
| AC5 | `.owlbear/doc-index.md:175,177,178,179` | td:0 | PASS |
| AC6 | `serve/kanban/src/owlbear_kanban/dispatch.py:139`; `tests/test_dispatch_gate_port_1214.py:20` | durable regression | PASS |

### Test Integrity
- No evidence in the current workspace that the builder weakened `TestFromAC_*` assertions.
- Commit diff was not available from task notes, so immutability verification is lower confidence than a direct diff audit.

### Builder Process Quality
- CLEAN: one builder cycle, no prior `## Review Evidence` section in the task body, no loop pattern detected.

### Deductions
- 0.10: AC1 proof gap. No executable check for root namespace removal.
- 0.04: AC2 proof gap. No executable check that the durable export test stopped treating `pick_dispatchable` as an `existing` baseline symbol.
- 0.02: No direct commit diff or dirty-tree contamination proof available through the current tool surface.

### Verdict
- FAIL
- Confidence: 0.84
- Route: `todo`
- Reason: implementation appears correct and executable evidence is green, but the task-local proof does not fully enforce the refined AC.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add an executable test that fails if `pick_dispatchable` is still bound on the `owlbear_kanban` root namespace after removal from `__all__` | `tests/test_init_exports_1350.py`, `serve/kanban/src/owlbear_kanban/__init__.py` | AC1 review gap: `tests/test_init_exports_1350.py:20-27` checks `__all__` and docstring only; no root-namespace absence check found in `tests/` |
| 2 | test-writer | Add a structural assertion that `tests/test_init_exports_1213.py` no longer treats `pick_dispatchable` as an `existing` baseline export, not just that one positive test was removed and one negative assertion was added | `tests/test_init_exports_1350.py`, `tests/test_init_exports_1213.py` | AC2 review gap: `tests/test_init_exports_1213.py:50-68` contains the baseline set, but `tests/test_init_exports_1350.py:33-43` does not assert that cleanup directly |
[[2026-05-05]]
## Test-Writer Notes

- Retry cycle (reviewer FAIL → test-writer gap fill)
- Test file: `tests/test_init_exports_1350.py`
- **2 new tests added** to fill reviewer-identified proof gaps:
  - `TestFromAC_DispatchExportRemoval::test_pick_dispatchable_absent_from_root_namespace` — AC1 gap: asserts `not hasattr(owlbear_kanban, "pick_dispatchable")` (root namespace absence, not just `__all__` absence)
  - `TestFromAC_TestFileSurgery::test_existing_set_pruned_of_pick_dispatchable` — AC2 gap: parses `existing = {...}` block in `test_init_exports_1213.py` via regex and asserts `pick_dispatchable` is not listed there
- Step 1b.1 applied: both new tests PASS against current implementation (builder already correct; only proof was missing)
- Quality-runner result: 50 passed, 0 failed; ruff clean; `owlbear_kanban.__init__` 100% coverage
- Builder skip: test-only retry, all tests green — advancing directly to review
[[2026-05-05]]
## Builder Notes
- Implementation: no code changes in this retry builder cycle (test-only retry from test-writer).
- Tests: 70 passed, 0 failed, 0 skipped via scoped quality-runner on `tests/test_init_exports_1350.py`, `tests/test_init_exports_1213.py`, `tests/test_dispatch_gate_port_1214.py`, and `tests/test_cockpit_boundary.py`.
- Coverage: `owlbear_kanban.__init__` at 100% (6/6 statements).
- Ruff: clean on `serve/kanban/src/owlbear_kanban/__init__.py`, `tests/test_init_exports_1350.py`, `tests/test_init_exports_1213.py`, `tests/test_dispatch_gate_port_1214.py`, and `tests/test_cockpit_boundary.py`.
- Evidence summary: reviewer-identified proof gaps are now covered by test-writer retry tests; scoped GREEN verification confirms AC-aligned behavior without additional implementation edits.
- Fixes applied: none required; existing implementation satisfies task expectations.

### Post-task Reflection
- Problem faced: task was in a test-proof retry state where implementation and proof timelines diverged.
- Workaround applied: treated builder cycle as verification-only and ran a scoped gate including adjacent regression coverage.
- Pattern discovered: when reviewer findings are proof-only and new tests pass against current code, builder should avoid unnecessary churn.
- Time sink: none in this cycle.
- Quality gap addressed: independent quality-runner verification now confirms the retry tests and durable regressions are both green.
[[2026-05-05]]
## Review Evidence

### Test Results
- Quality-runner scoped pass: 70 passed, 0 failed, 0 skipped across tests/test_init_exports_1350.py, tests/test_init_exports_1213.py, tests/test_dispatch_gate_port_1214.py, and tests/test_cockpit_boundary.py.
- No environment errors reported by quality-runner.

### Lint Results
- Ruff clean on serve/kanban/src/owlbear_kanban/__init__.py, tests/test_init_exports_1350.py, tests/test_init_exports_1213.py, tests/test_dispatch_gate_port_1214.py, and tests/test_cockpit_boundary.py.

### Coverage
- owlbear_kanban.__init__: 100% statement coverage.
- Scoped run reported 31% overall, but the review gate here is diff-scoped to the touched module and adjacent regression files.

### Test-Writer Audit
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 remove pick_dispatchable from root import/export surface and docstring | tests/test_init_exports_1350.py::TestFromAC_DispatchExportRemoval::{test_pick_dispatchable_absent_from_dunder_all,test_module_docstring_no_longer_advertises_pick_dispatchable,test_pick_dispatchable_absent_from_root_namespace} | Yes. The trio independently proves __all__ absence, docstring cleanup, and root-namespace absence. | COVERED |
| AC2 update durable export tests | tests/test_init_exports_1350.py::TestFromAC_TestFileSurgery::{test_positive_pick_dispatchable_test_removed,test_negative_assertion_present,test_existing_set_pruned_of_pick_dispatchable} | Yes. The retry test closes the prior proof gap by asserting the existing baseline set no longer contains pick_dispatchable. | COVERED |
| AC3 remove Dispatch helper subsection from README | td:0 artifact check only | Yes via direct file inspection: no pick_dispatchable match remains in serve/kanban/README.md and the README now flows from Launch / Usage to KanbanEngine methods and AgentView dispatch pipeline. | COVERED |
| AC4 fix README edit_task example | td:0 artifact check only | Yes via direct file inspection: serve/kanban/README.md:26 now uses engine.edit_task("42", add_tags=["phase-1"]). | COVERED |
| AC5 regenerate .owlbear/doc-index.md | td:0 artifact check only | Yes via direct file inspection: .owlbear/doc-index.md:175-182 mirrors the current kanban README headings. | COVERED |
| AC6 preserve direct module-path compatibility | Durable regression: tests/test_dispatch_gate_port_1214.py::TestFromAC_PickDispatchableDeprecation::test_pick_dispatchable_emits_deprecation_warning | Yes. dispatch.py still defines pick_dispatchable and the direct import/deprecation-path regression stayed green. | COVERED |

### Test Integrity
- No evidence that the builder weakened or removed TestFromAC assertions in the current workspace snapshot.
- Current task tests contain the two retry assertions added after the prior reviewer FAIL: tests/test_init_exports_1350.py:30-32 and tests/test_init_exports_1350.py:50-57.
- Commit-log evidence shows the expected sequence for this task: test-writer RED commit 3e2be56050732a813e838d6d2e2ec03d39910329, builder implementation commit 889bf67b7258e239dcfa3c0e6c6ac0b1bd4de4d9, then test-writer retry-gap commit e2874b98d28cab04436865d7183e48989c02dd43.
- Direct diff-scoped immutability proof was not available because git status/diff execution was unavailable through the current tool surface.

### Security / Data Safety
- No new dependency, persistence, boundary-validation, or secret-handling surface was introduced by this task.
- Workspace search found no first-party serve/* caller of pick_dispatchable beyond serve/kanban/src/owlbear_kanban/dispatch.py itself; the only live import consumer remains the intended compatibility regression in tests/test_dispatch_gate_port_1214.py.

### Builder Process Quality
- CLEAN. There was one prior Review Evidence section (proof-gap FAIL), followed by a test-writer retry and a builder verification-only cycle. No repeated failing review loop is present in the current state.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | serve/kanban/src/owlbear_kanban/__init__.py:9-29; tests/test_init_exports_1350.py:21-32 | test_pick_dispatchable_absent_from_dunder_all; test_module_docstring_no_longer_advertises_pick_dispatchable; test_pick_dispatchable_absent_from_root_namespace | PASS |
| AC2 | tests/test_init_exports_1213.py:52-68; tests/test_init_exports_1350.py:38-57 | test_positive_pick_dispatchable_test_removed; test_negative_assertion_present; test_existing_set_pruned_of_pick_dispatchable | PASS |
| AC3 | serve/kanban/README.md:31,52 and no pick_dispatchable matches in the file | td:0 | PASS |
| AC4 | serve/kanban/README.md:26 | td:0 | PASS |
| AC5 | .owlbear/doc-index.md:175-182 | td:0 | PASS |
| AC6 | serve/kanban/src/owlbear_kanban/dispatch.py:139-168; tests/test_dispatch_gate_port_1214.py:20,496 | direct import deprecation-path regression | PASS |

### Deductions
- 0.02: Could not run a direct git status contamination check in the current tool surface, so dirty-tree overlap is not fully proven.
- 0.01: Could not obtain a direct commit diff for TestFromAC immutability; mitigated by commit-log sequence plus current file inspection.

### Verdict
- PASS
- Confidence: 0.95
- Action: advance to docs.
[[2026-05-05]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated/Verified | `serve/kanban/README.md` — removed Dispatch helper subsection (no `pick_dispatchable` match), correct `edit_task("42", add_tags=["phase-1"])` at line 26. Builder already made changes; verified accurate. |
| 2 | Module docstrings | Yes | Verified | `serve/kanban/src/owlbear_kanban/__init__.py` module docstring: "Exports the transport-free kanban engine, its public models, error classes." — no mention of `pick_dispatchable`. Accurate. |
| 3 | External attribution | No | N/A | No external patterns used; internal deprecation-removal only. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` doc was produced for this task. |
| 5 | Diagram maintenance | Yes | Updated | `share/diagrams/kanban.excalidraw` and `share/diagrams/mcp-topology.excalidraw` both have `describes: serve/kanban/src/**` — footers updated to `Last verified: 2026-05-05 (f3b98b0c)`. Committed: `290e8b49`. |
| 6 | Explicit diagram creation | No | N/A | No new diagram creation requested. |
| 7 | Deletion detection | No | N/A | No IN-scope files deleted. `dispatch.py` explicitly preserved (AC6). No orphaned docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/__init__.py` | IN (docstrings) | Verified — docstring accurate |
| `serve/kanban/README.md` | IN (package README) | Verified — builder changes correct |
| `.owlbear/doc-index.md` | IN (advisory) | Verified — headings match README |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |
| `tests/test_init_exports_1350.py` | OUT (test) | N/A |
| `tests/test_init_exports_1213.py` | OUT (test) | N/A |
| `tests/test_dispatch_gate_port_1214.py` | OUT (test) | N/A |
| `tests/test_cockpit_boundary.py` | OUT (test) | N/A |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer timestamp
- `share/diagrams/mcp-topology.excalidraw` — footer timestamp

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1350-*` files found)
[[2026-05-05]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 remove pick_dispatchable from root export/import, update docstring | __init__.py:9-29 has no pick_dispatchable; test_init_exports_1350.py::test_pick_dispatchable_absent_from_dunder_all, test_module_docstring_no_longer_advertises_pick_dispatchable, test_pick_dispatchable_absent_from_root_namespace all PASS | PASS |
| AC2 update durable export tests (remove positive, prune existing set, add negative) | test_init_exports_1213.py:52-68 (existing set pruned); test_init_exports_1350.py:38-57 (structural surgery tests all PASS) | PASS |
| AC3 remove Dispatch helper subsection from README | serve/kanban/README.md has no "Dispatch helper" or "pick_dispatchable(tasks)" | PASS |
| AC4 fix edit_task example | serve/kanban/README.md:26 uses engine.edit_task("42", add_tags=["phase-1"]) | PASS |
| AC5 regenerate doc-index | .owlbear/doc-index.md:175-182 mirrors current README headings | PASS |
| AC6 preserve dispatch.py and direct import path | dispatch.py intact; test_dispatch_gate_port_1214.py stayed green (70 passed scoped run) | PASS |

### Test Results
- pytest (full suite): 4570 passed, 200 failed (all unrelated), 4 skipped. Zero failures in task scope.
- ruff: clean on all task-relevant files.

### Architect Quality: 4/5
AC refined from 8 vague/conditional lines to 6 precise td-annotated lines with challenger override and dependency analysis. One reviewer proof-gap FAIL triggered a test-writer retry, suggesting minor test-depth gaps in original AC, but all resolved cleanly without builder churn.

### Deduction Breakdown
- 0.02: cannot prove zero dirty-tree contamination via git diff (tool surface limitation)
- No AC evidence gaps, no lint violations, no task-scope failures, no missing reviewer section.

### Confidence: 0.98
### Action: archive

### Commit Integrity
| Commit | Type | Role | Note |
|--------|------|------|------|
| 3e2be56 | test | test-writer | RED phase |
| 889bf67 | feat | builder | implementation |
| e2874b9 | test | test-writer | retry gap fill |
| 290e8b4 | docs | doc-writer | diagram footers |