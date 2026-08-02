---
id: 1267
title: 'P1-01: Remove SQLite code and legacy tests from mcp-memory'
status: archived
priority: medium
created: 2026-05-02T03:43:26.887977+00:00
updated: 2026-05-02T06:23:47.164014+00:00
tags:
- phase-1
- scope:mcp-memory
- cleanup
parent: 1266
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Remove all SQLite-based code from `serve/mcp-memory/` and its legacy tests. Clear the module for the new file-based engine.

Brief: see parent #1266

## Scope

**In scope:**
- Delete `server.py` (SQLite DDL, connection management)
- Delete `migrate.py` (migration utilities)
- Delete `approve.py` (SQLite approval logic)
- Delete `tools.py` (old SQLite-backed tool implementations)
- Delete `tests/test_server.py` and `tests/test_package.py`
- Clean `__init__.py` and `__main__.py` to empty stubs
- Remove any alembic/migration artifacts if present

**Out of scope:**
- Writing new code (handled by subsequent tasks)
- Modifying `pyproject.toml` deps (handled by engine task)
- Modifying `models.py` (replaced in #1269)

## Acceptance Criteria

- [ ] No SQLite imports remain in `serve/mcp-memory/src/`
- [ ] No `*.db` files or migration scripts in the package
- [ ] Old test files removed (`test_server.py`, `test_package.py`)
- [ ] Module still importable (empty `__init__.py` at minimum)
- [ ] `uv run pytest serve/mcp-memory/tests/` passes (no tests = pass)
[[2026-05-02]]
## Test-Writer Notes
- Test file: tests/test_mcp_memory_1267.py
- Classes: TestFromAC_NoSQLiteImports, TestFromAC_NoMigrationScripts, TestFromAC_LegacyTestFilesRemoved, TestFromAC_ModuleStub, TestFromAC_TestDirEmpty
- Tests per category: structural/deletion checks (no happy/edge/error/boundary split — all AC lines are presence/absence assertions)
- Total: 10 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1: No SQLite imports in src/ | test_no_sqlite3_import_in_any_source_file, test_server_py_deleted, test_approve_py_deleted, test_tools_py_deleted |
| AC2: No migration scripts | test_migrate_py_deleted |
| AC3: Old test files removed | test_test_server_py_removed, test_test_package_py_removed |
| AC4: __main__.py is empty stub | test_main_py_has_no_server_import, test_main_py_has_no_mcp_run_call |
| AC5: Package tests dir empty | test_no_test_files_remain_in_package_tests |

Failure evidence: all 10 tests assert absence of files/imports that currently exist.
[[2026-05-02]]
## Builder Notes
- Implementation: cleaned stubs in `serve/mcp-memory/src/owlbear_mcp_memory/__init__.py` and `serve/mcp-memory/src/owlbear_mcp_memory/__main__.py`; removed legacy SQLite modules `server.py`, `migrate.py`, `approve.py`, `tools.py`; removed legacy package tests `serve/mcp-memory/tests/test_server.py` and `serve/mcp-memory/tests/test_package.py`.
- Tests: 10/10 `TestFromAC_*` passed via quality-runner on `tests/test_mcp_memory_1267.py`.
- Coverage: N/A for this deletion-only structural task (quality-runner reported no meaningful module coverage collection in scoped run).
- ruff: clean (scoped lint on `serve/mcp-memory/src/owlbear_mcp_memory` and `tests/test_mcp_memory_1267.py`).
- Evidence summary: RED verified first (10 failing tests), then GREEN after deletions/stub cleanup (0 failures). `rg` check confirmed no `sqlite3` imports remain under `serve/mcp-memory/src/owlbear_mcp_memory`.
- Fixes applied: resolved patch-delete drift by force-removing files and re-verifying filesystem state before final gate.

### Post-task Reflection
- problems_faced: delete patches reported success while files remained.
- workarounds_applied: switched to direct `rm -f` with explicit `ls` + `rg` verification.
- patterns_discovered: always verify physical deletion before re-running AC checks.
- time_sinks: repo-level pytest addopts/xdist complicates no-test directory assertions.
- quality_gaps: coverage percentage is not a useful signal for file-removal-only tasks.

[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped on `tests/test_mcp_memory_1267.py`: 10 passed, 0 failed, 0 skipped
- supplemental quality-runner on `tests/test_memory_models_1268.py`: 34 passed, 0 failed; collection imports `owlbear_mcp_memory.models`, so the package import path still works
- supplemental quality-runner on `serve/mcp-memory/tests/`: 0 collected, 0 failed, pytest exit 5 (`no tests collected`); runner classified this as the expected empty-directory outcome for the AC
- td:1 task, so no code-reader dispatch

### Lint
- quality-runner scoped lint: clean

### Coverage
- task-scoped run: not collected for this deletion-only structural task
- supplemental importability run: `owlbear_mcp_memory.__init__` 100%, `owlbear_mcp_memory.__main__` 100%, `owlbear_mcp_memory.models` 100%

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|----------------|----------------------------|---------|
| No SQLite imports remain in `serve/mcp-memory/src/` | `test_no_sqlite3_import_in_any_source_file`, `test_server_py_deleted`, `test_approve_py_deleted`, `test_tools_py_deleted` | Yes; exact absence assertions fail on any surviving `sqlite3` import or legacy file | COVERED |
| No `*.db` files or migration scripts in the package | `test_migrate_py_deleted` | Yes for migration script deletion; package file search also found no `*.db` files | COVERED |
| Old test files removed (`test_server.py`, `test_package.py`) | `test_test_server_py_removed`, `test_test_package_py_removed`, `test_no_test_files_remain_in_package_tests` | Yes; exact absence assertions fail if any legacy package test file remains | COVERED |
| Module still importable (empty `__init__.py` at minimum) | `test_main_py_has_no_server_import`, `test_main_py_has_no_mcp_run_call` | Partially; task-local tests prove the `__main__.py` stub shape, but not `__init__.py` importability by themselves. Supplemental quality-runner on `tests/test_memory_models_1268.py` closes the proof gap | LAX |
| `uv run pytest serve/mcp-memory/tests/` passes (no tests = pass) | `test_no_test_files_remain_in_package_tests` | Partially; task-local test proves empty directory state, while the supplemental directory-path quality-runner pass proves the AC's command outcome | LAX |

#### Security Review
- No OWASP-class issue in the live package state. The remaining package code is a stubbed entry surface plus `engine.py` and `models.py`; no secrets, injection, traversal, or unsafe deserialization patterns were found in the reviewed scope.

#### Test Integrity
- Live `TestFromAC_*` classes and method names match the test-writer note.
- No weakened or removed assertions were observed in the live task test file.
- Commit-level immutability is not fully provable without a diff, so this carries a small confidence deduction only.

#### Test Quality
- STRONG: exact absence assertions on `sqlite3` imports and deleted files.
- ADEQUATE: AC4 and AC5 rely on supplemental executable proof outside the task-local `TestFromAC_*` file.
- STRONG: descriptive test names and no shared mutable fixture state.

#### Data Safety
- No data-safety issue in the live package state.

#### Implementation-Aware Gaps
- No blocking implementation gap remains for this task's scope.
- `serve/mcp-memory/src/owlbear_mcp_memory/` now contains only `__init__.py`, `__main__.py`, `engine.py`, and `models.py`.
- Source search over `serve/mcp-memory/src/**/*.py` found no `sqlite3` or `.db` matches.
- File search found no `serve/mcp-memory/**/*.db` and no `serve/mcp-memory/**/alembic*` artifacts.

#### Builder Process Quality
- CLEAN. No prior `## Review Evidence` section was present for task 1267, so this is the first review cycle.

### Pass 2 - INFORMATIONAL
- `serve/mcp-memory/README.md` line 35 still documents `OWLBEAR_MEMORY_DB_PATH` and a SQLite database. That doc drift is outside this task's AC, but the docs phase should clean it up.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| No SQLite imports remain in `serve/mcp-memory/src/` | `tests/test_mcp_memory_1267.py` lines 26-33 and 35-49 use exact absence assertions; live source search found no `sqlite3` or `.db` matches under `serve/mcp-memory/src/**/*.py` | `TestFromAC_NoSQLiteImports` | PASS |
| No `*.db` files or migration scripts in the package | `tests/test_mcp_memory_1267.py` lines 55-59 assert `migrate.py` is gone; file search found no `serve/mcp-memory/**/*.db` and no `serve/mcp-memory/**/alembic*` | `TestFromAC_NoMigrationScripts` | PASS |
| Old test files removed (`test_server.py`, `test_package.py`) | `tests/test_mcp_memory_1267.py` lines 67-75 and 103-110 assert both specific files and the absence of any remaining `test_*.py`; live package test dir contains only `__pycache__/` | `TestFromAC_LegacyTestFilesRemoved`, `TestFromAC_TestDirEmpty` | PASS |
| Module still importable (empty `__init__.py` at minimum) | `serve/mcp-memory/src/owlbear_mcp_memory/__init__.py` line 1 and `__main__.py` line 1 are stub docstrings; supplemental quality-runner on `tests/test_memory_models_1268.py` collected and passed 34 tests, proving imports from `owlbear_mcp_memory.models` succeed | `TestFromAC_ModuleStub` plus supplemental import proof | PASS |
| `uv run pytest serve/mcp-memory/tests/` passes (no tests = pass) | supplemental quality-runner on `serve/mcp-memory/tests/` reported 0 collected, 0 failed, pytest exit 5 (`no tests collected`) and explicitly classified that as the expected empty-directory AC outcome; `tests/test_mcp_memory_1267.py` lines 103-110 prove the directory is empty of `test_*.py` | `TestFromAC_TestDirEmpty` plus supplemental directory run | PASS |

### Deductions
- -0.03: TestFromAC immutability could not be fully proven without commit diff access
- -0.02: AC4 importability proof depends on supplemental suite execution, not only the task-local `TestFromAC_*` file
- -0.01: AC5 command-outcome proof depends on a supplemental directory-path runner invocation, not only the task-local `TestFromAC_*` file
- Confidence: 0.94

### Verdict
- PASS. The live package state satisfies this task's cleanup contract; remaining concerns are proof-shape deductions only.

### Action
- Advance to docs.
- During docs phase, remove stale SQLite references from `serve/mcp-memory/README.md`. 
[[2026-05-02]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | Reviewer explicitly flagged `serve/mcp-memory/README.md` line 35 (SQLite config) and description (SQLite-backed); also updated root `README.md` — removed Memory Migration + Memory Approval sections (referenced deleted `migrate.py` and `approve.py`); removed "(SQLite-backed)" from directory layout table |
| 2 | Module docstrings | No | N/A | Only deleted source files and empty stubs (`__init__.py`, `__main__.py`) — no public classes or functions to document |
| 3 | External attribution | No | N/A | Deletion-only structural task; no external patterns used |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/memory-layers.excalidraw` has `describes: serve/mcp-memory/src/**` — footer updated to `Last verified: 2026-05-02 (ae25f07a)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body |
| 7 | Deletion detection | Yes | Noted | Deleted files (`server.py`, `migrate.py`, `approve.py`, `tools.py`) were referenced in `serve/mcp-memory/README.md` and root `README.md` — both IN-scope docs updated directly under Item 1 (behavior change update, not orphaned doc deletion) |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-memory/src/owlbear_mcp_memory/server.py` | OUT (deleted .py — logic) | N/A |
| `serve/mcp-memory/src/owlbear_mcp_memory/migrate.py` | OUT (deleted .py — logic) | N/A |
| `serve/mcp-memory/src/owlbear_mcp_memory/approve.py` | OUT (deleted .py — logic) | N/A |
| `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` | OUT (deleted .py — logic) | N/A |
| `serve/mcp-memory/src/owlbear_mcp_memory/__init__.py` | OUT (stub, no public API) | N/A |
| `serve/mcp-memory/src/owlbear_mcp_memory/__main__.py` | OUT (stub, no public API) | N/A |
| `serve/mcp-memory/tests/test_server.py` | OUT (deleted test) | N/A |
| `serve/mcp-memory/tests/test_package.py` | OUT (deleted test) | N/A |
| `serve/mcp-memory/README.md` | IN | Updated — removed SQLite description, replaced Configuration section |
| `README.md` | IN | Updated — removed Memory Migration section, Memory Approval section, "(SQLite-backed)" from directory layout |
| `share/diagrams/memory-layers.excalidraw` | IN | Updated footer only |

### Files Updated
- `serve/mcp-memory/README.md` — description "SQLite-backed" → "file-based"; Configuration section replaced (removed stale `OWLBEAR_MEMORY_DB_PATH`)
- `README.md` — removed Memory Migration and Memory Approval sections; updated directory layout row
- `share/diagrams/memory-layers.excalidraw` — footer updated to `Last verified: 2026-05-02 (ae25f07a)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1267-*` files found)

Commit: c9000b43
[[2026-05-02]]
## Planning

Created follow-up task #1275 "Fix stale test assertions in test_mcp_memory_1267.py" at backlog under epic #1266. Tags: scope:mcp-memory, cleanup. priority: medium. Four stale file-absence assertions need updating or removal now that subsequent epic tasks recreated those files with new implementations.[[2026-05-02]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| No SQLite imports in src/ | test_no_sqlite3_import_in_any_source_file PASSES; rg confirmed no sqlite3 in src/ | PASS |
| No *.db/migration scripts | test_migrate_py_deleted PASSES; no *.db files found | PASS |
| Old test files removed | test_test_server_py_removed, test_test_package_py_removed PASS; package tests/ has only __pycache__ | PASS |
| Module importable | __init__.py is stub docstring; imports work (proven by sibling suites) | PASS |
| pytest on package tests/ passes | test_no_test_files_remain PASSES; quality-runner exit 5 (0 collected) | PASS |

### Test Results
- pytest (task-scoped): 6 passed, 4 failed (stale assertions from subsequent epic work)
- pytest (full suite, excl SSE): 683 passed, 4 failed (pre-existing kanban debt, unrelated)
- 4 task-test failures: test_server_py_deleted, test_tools_py_deleted, test_main_py_has_no_server_import, test_main_py_has_no_mcp_run_call. Caused by subsequent epic tasks recreating server.py/tools.py/__main__.py with new file-based implementations. Underlying AC (no SQLite) satisfied.
- ruff: clean

### Upstream Commits
- test-writer: fac18745
- builder: feca40f6
- docs: c9000b43

### Architect Quality: 4/5
AC lines specific and verifiable. Minor gap: scope listed file deletions as permanent but epic plan intended recreation, leading test-writer to assert file absence rather than SQLite absence.

### Deduction Breakdown
- Task-scoped test failures (4 stale tests): -.05

### Confidence: .95
### Action: archive

### Follow-up
- #1275: Fix stale test assertions in test_mcp_memory_1267.py (backlog)
