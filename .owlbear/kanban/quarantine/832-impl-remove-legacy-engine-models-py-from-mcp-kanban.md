---
id: 832
title: Impl — Remove legacy engine_models.py from mcp-kanban
status: archived
priority: needed
created: '2026-04-11T11:41:14.187673+00:00'
updated: '2026-04-11T20:14:51.501648+00:00'
tags:
- kanban
- phase-2
- scope:mcp-kanban
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `engine_models.py` deleted from `serve/mcp-kanban/src/owlbear_mcp_kanban/`
- Any remaining imports of `owlbear_mcp_kanban.engine_models` migrated to `owlbear_kanban.models` (or `owlbear_kanban`)
- Preceding RED tests pass GREEN
- All 8 MCP tool tests pass

## Context

Phase 2 cleanup. Completes the extraction gap identified in #818 review.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
File: `serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py` (DELETE)
[[2026-04-11]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Delete one legacy file + migrate its imports — tightly coupled, not splittable |
| Interface clarity | PASS | AC1 specifies exact file path; AC2 specifies source/target modules; AC3/AC4 define test gates |
| Dependency correctness | PASS | #831 (RED test) at `todo`; dependency enforced by AC3 ("Preceding RED tests pass GREEN"). `depends_on` field empty — orchestrator should set `depends_on: [831]` |
| Module layering | PASS | Removes a duplicate; imports point down from mcp-kanban → kanban (correct direction) |
| TDD compliance | PASS | Paired with #831 (test task) at `todo` |
| KISS/YAGNI | PASS | Minimal scope — 1 file deletion + 3 import rewrites |
| Premise challenge | PASS | `engine_models.py` is a confirmed 1:1 duplicate of `owlbear_kanban.models` (minus TaskSummary). #818 review identified the missed deletion. Removal is warranted |
| Pattern consistency | PASS | Same extraction pattern as engine.py, task_io.py, config_loader.py, activity_log.py, agent_names.py — all deleted in #818 |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Kanban domain only |

### Builder Guidance

**Files to modify (AC2):** Exactly 3 test files import from the legacy module — zero production files do:

- `tests/test_kanban_task_io.py:26` — `from owlbear_mcp_kanban.engine_models import TaskRecord` → `from owlbear_kanban.models import TaskRecord`
- `tests/test_kanban_mcp_migration.py:20` — `from owlbear_mcp_kanban.engine_models import TaskRecord` → `from owlbear_kanban.models import TaskRecord`
- `tests/test_rename_taskrecord_to_task_799.py:21` — `from owlbear_mcp_kanban.engine_models import Task, TaskRecord` → `from owlbear_kanban.models import Task, TaskRecord`

**Production code:** `server.py` already imports from `owlbear_kanban` (line 16) and TYPE_CHECKING imports `owlbear_kanban.models.TaskRecord` (line 22). No changes needed.

**AC4 verification:** Run `pytest serve/mcp-kanban/tests/` — the 8 tool functions are: create_task, edit_task, end_work, list_tasks, move_task, pick_tasks, show_task, start_work.

### Challenge Results

- Challenger: PROCEED (confidence 0.85)
- Concerns: AC2 could name specific files; missing `depends_on`; AC4 could cite test file
- Architect response: ACCEPTED — addressed via builder guidance above. AC text is precise enough; naming files in guidance prevents misses without over-specifying the AC itself

### Verdict: APPROVE

### Action Taken: Advanced to `todo`. Builder guidance appended with exact file-level migration map. Orchestrator should set `depends_on: [831]`

[[2026-04-11]]

## Test-Writer Notes

- Test file: tests/test_remove_legacy_engine_models_832.py
- Classes: TestFromAC_ServerToolsAfterEngineModelsRemoval
- Tests per category: happy 2, edge 2, error 1, boundary 1
- Total: 6 tests, all FAIL
- ruff: clean
- Commit: 1e1f625b

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 (engine_models.py deleted — precondition) | All 6 tests assert `not _ENGINE_MODELS_PATH.exists()` as first assertion; `test_engine_models_not_importable_as_submodule` also fails via `importlib.util.find_spec` independently |
| AC4 (all 8 MCP tools pass) | `test_all_8_tools_importable_from_server_module`, `test_all_8_tool_names_in_server_all_exports`, `test_mcp_server_registers_exactly_8_tools` |
| AC4 — pick_tasks gap | `test_pick_tasks_registered_in_mcp_server`, `test_pick_tasks_has_read_only_hint` — `pick_tasks` (8th tool) was absent from `test_tool_annotations_494.py` parametrize; these fill that gap |

### Relationship to #831

AC1+AC2 are fully covered by `tests/test_remove_legacy_engine_models_831.py` (filesystem check + AST workspace scan). This file covers AC4 specifically — that deletion doesn't degrade the server's 8-tool public API. All 6 tests fail in RED because `engine_models.py` still exists; the precondition assertion at the top of each test gates progress clearly for the builder.

### Failure modes confirmed

- Tests 1–5: `AssertionError: AC1 precondition: engine_models.py still exists`
- Test 6: `AssertionError: owlbear_mcp_kanban.engine_models is still importable as a Python module`
[[2026-04-11]]

## Builder Notes

### Files Changed

- None — `engine_models.py` was already absent from `serve/mcp-kanban/src/owlbear_mcp_kanban/` (deleted by prior work, consistent with #831). The 3 test files listed in AC2 builder guidance already had their imports migrated.

### Test Results

- `tests/test_remove_legacy_engine_models_832.py` — **6/6 passed** (all `TestFromAC_*` tests GREEN)
- `tests/test_remove_legacy_engine_models_831.py` — **2/2 passed** (AC1/AC2 preconditions)
- `serve/mcp-kanban/tests/` — **19/19 passed** (all 8 MCP tool tests confirmed)

### Coverage

- AC1: `engine_models.py` absent ✓ (`_ENGINE_MODELS_PATH.exists()` → False)
- AC2: No imports of `owlbear_mcp_kanban.engine_models` found anywhere ✓
- AC3: RED tests from #831 pass GREEN ✓
- AC4: All 8 MCP tools (`create_task`, `edit_task`, `end_work`, `list_tasks`, `move_task`, `pick_tasks`, `show_task`, `start_work`) importable, registered, and annotated correctly ✓

### Lint

- `ruff check` on all affected paths: **clean**

### Evidence Summary

Pre-flight inspection showed `engine_models.py` was not present in the package directory (only `models.py`, `server.py`, `__init__.py`, `__main__.py`). Grep confirmed zero workspace occurrences of `from owlbear_mcp_kanban.engine_models import`. State fully satisfies AC — no code changes required.
[[2026-04-11]]

## Review Evidence

### Test Results (independently verified)

| File | Passed | Failed |
|------|--------|--------|
| tests/test_remove_legacy_engine_models_832.py | 6 | 0 |
| tests/test_remove_legacy_engine_models_831.py | 2 | 0 |
| serve/mcp-kanban/tests/ | 19 | 0 |
| **Total** | **27** | **0** |

Note: quality-runner first run failed (pytest-xdist `-n auto` hang). Rerun with `-p no:xdist` succeeded cleanly.

### Lint

ruff: **clean** — zero violations on `serve/mcp-kanban/src/` and both test files.

### Coverage

owlbear_mcp_kanban overall: 41% (server.py 36%, models.py 88%, **init**.py 100%). No deduction — zero production files were touched (deletion task; pre-existing coverage state).

### Source Control

Builder reported zero file changes for this task. No `engine_models.py` appears in the changed-files list (89 total unstaged changes are residuals from upstream tasks). The deletion was pre-completed before this task was actioned.

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1: engine_models.py deleted | Directory listing: absent. importlib.util.find_spec returns None. test_831 `test_engine_models_py_does_not_exist` passes. | ✅ PASS |
| AC2: No remaining `owlbear_mcp_kanban.engine_models` imports | AST workspace scan (test_831); grep scan; 3 flagged test files confirmed migrated to `owlbear_kanban.models`. Zero occurrences. | ✅ PASS |
| AC3: Preceding RED tests (831) pass GREEN | test_remove_legacy_engine_models_831.py: 2/2 pass. | ✅ PASS |
| AC4: All 8 MCP tool tests pass | serve/mcp-kanban/tests/: 19/19 pass. pick_tasks gap in test_tool_annotations_494.py filled by 832 tests. | ✅ PASS |

### TestFromAC_ Integrity

| Test Method | AC | Would Fail If Violated? | Quality |
|-------------|----|-----------------------|---------|
| test_all_8_tools_importable_from_server_module | AC1+AC4 | YES — import failure or non-callable caught | Strong |
| test_all_8_tool_names_in_server_all_exports | AC4 | YES — set difference detected | Strong |
| test_pick_tasks_registered_in_mcp_server | AC4 (gap fill) | YES — membership check on registered tools | Strong |
| test_pick_tasks_has_read_only_hint | AC4 (gap fill) | YES — annotation.readOnlyHint is True enforced | Strong |
| test_mcp_server_registers_exactly_8_tools | AC4 (boundary) | YES — dual checks: missing + extra | Strong |
| test_engine_models_not_importable_as_submodule | AC1 | YES — importlib returns None asserted | Strong |

No TestFromAC_ modifications detected vs test-writer's intent. No LAX assertions. All error messages actionable.

### Security

None. Tests use only stdlib (pathlib, ast, importlib). No shell commands, file writes, or network calls.

### Deductions

None.

### Verdict

**Confidence: 0.96 → PASS #832 → docs**
[[2026-04-11]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure deletion of a legacy duplicate. Zero production files touched. 8 MCP tools unchanged. `copilot-instructions.md` contains no `engine_models` or `owlbear_mcp_kanban` module inventory — no update needed. |
| 2 | Module docstrings | No | N/A | Builder notes: "Files Changed: None." No Python modules created or modified. |
| 3 | External attribution | No | N/A | Internal cleanup task; no external patterns or articles referenced. `.owlbear/sources/overview.md` verified — no `engine_models` entry present. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. README.md verified — no `engine_models` reference. |
| 5 | Research doc | No | N/A | No `.owlbear/research/` file produced. Task references architecture brief only. |

### Files Updated

- None

### Scratch Files Cleaned

- None (file_search for `.owlbear/scratch/832-*` returned no results)
[[2026-04-11]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: engine_models.py deleted | `Test-Path` → False; dir listing: absent; `test_engine_models_py_does_not_exist` PASS | PASS |
| AC2: No remaining imports | Reviewer AST scan + grep; `test_no_workspace_imports_from_engine_models` PASS | PASS |
| AC3: Preceding RED tests pass GREEN | `test_remove_legacy_engine_models_831.py` 2/2 PASS | PASS |
| AC4: All 8 MCP tool tests pass | `serve/mcp-kanban/tests/` 19/19 PASS; `test_remove_legacy_engine_models_832.py` 6/6 PASS | PASS |

### Test Results

- pytest (task-scoped): 27 passed, 0 failed
- pytest (full suite): 3533 passed, 285 failed, 6 errors — zero failures in task scope; all failures are pre-existing stale tests from prior tasks
- ruff: clean on task-scope files

### Architect Quality: 5/5

AC was precise: exact file path, specific migration target module, RED test dependency. Builder guidance named exact files and line numbers. Pattern-consistent with prior extraction tasks (#818).

### Deduction Breakdown

- AC lines without evidence: 0 → no deduction
- Lint violations: 0 → no deduction
- AC quality ≤ 3: No (5/5) → no deduction
- Missing reviewer evidence: No (detailed, PASS at .96) → no deduction
- Full-suite failures in task scope: 0 → no deduction

### Confidence: .98

### Action: archive

Note: Builder made zero code changes — file was already deleted by prior work. Task correctly verified the state via tests. Minor .02 deduction for 285 pre-existing full-suite failures (not in task scope, but preventing a fully clean run).
