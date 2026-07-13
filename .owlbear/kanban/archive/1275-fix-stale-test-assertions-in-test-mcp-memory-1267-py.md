---
id: 1275
title: Fix stale test assertions in test_mcp_memory_1267.py
status: archived
priority: medium
created: 2026-05-02T06:23:30.198676+00:00
updated: 2026-05-02T12:48:10.295416+00:00
tags:
- scope:mcp-memory
- cleanup
- type:test
parent: 1266
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Four tests in `tests/test_mcp_memory_1267.py` now fail because they assert file absence for `server.py`, `tools.py`, and `__main__.py` — files that were deleted by #1267 but recreated by subsequent epic #1266 children with new file-based implementations.

### Failing tests
- `test_server_py_deleted`
- `test_tools_py_deleted`
- `test_main_py_has_no_server_import`
- `test_main_py_has_no_mcp_run_call`

## Acceptance Criteria

- [ ] Remove the four stale test functions (`test_server_py_deleted`, `test_tools_py_deleted`, `test_main_py_has_no_server_import`, `test_main_py_has_no_mcp_run_call`) — `test_no_sqlite3_import_in_any_source_file` already covers the SQLite-absence invariant across all source files, making per-file deletion assertions redundant now that the files were recreated with non-SQLite implementations (td:0)
- [ ] If removing all tests from a class leaves it empty, remove the empty class too (td:0)
- [ ] `uv run pytest tests/test_mcp_memory_1267.py` passes (td:0)
- [ ] No other test files regress (td:0)

## Architecture Review

**Verdict:** APPROVED — simple test maintenance, all td:0

**AC Assessment:**

| AC line | Assessment | Action |
|---------|-----------|--------|
| Remove four stale tests | Clear, named targets, correct rationale | Refined from "update or remove" to "remove" — update path redundant with existing broader check |
| Remove empty classes | Added — prevents orphan class shells after deletion | New |
| pytest pass | Verifiable command | Kept as-is |
| No regression | Standard guard | Kept as-is |

**Architecture notes:**
- `server.py` now contains FastMCP server (`from mcp.server.fastmcp import ...`), no SQLite
- `tools.py` is markdown-backed (`from owlbear_mcp_memory.models import ...`), no SQLite
- `__main__.py` is a proper entry point again (`from owlbear_mcp_memory.server import mcp`)
- `test_no_sqlite3_import_in_any_source_file` (remaining in the same file) scans ALL `.py` files under `src/` — the SQLite invariant is still guarded
- Sibling test files `test_mcp_memory_1266.py` and `test_mcp_memory_1269.py` cover new implementations

**Dependency analysis:** No dependencies needed — all prerequisite changes (file recreation) already landed.

**Test-writer: SKIP** — all AC lines td:0 (mechanical test cleanup).

[[2026-05-02]]
APPROVED → todo. Refined AC: narrowed "update or remove" to "remove only" — the update path is redundant with existing `test_no_sqlite3_import_in_any_source_file`. Added empty-class cleanup AC. All td:0, Test-writer: SKIP. Tagged `type:test` for pass-through.
[[2026-05-02]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Task tagged `type:test`: mechanical removal of four stale test functions (`test_server_py_deleted`, `test_tools_py_deleted`, `test_main_py_has_no_server_import`, `test_main_py_has_no_mcp_run_call`) from `tests/test_mcp_memory_1267.py`.
- Architect confirmed "Test-writer: SKIP" — no new tests applicable.
- Passing through to builder.
[[2026-05-02]]
## Builder Notes
- Implementation: removed stale tests from tests/test_mcp_memory_1267.py (`test_server_py_deleted`, `test_tools_py_deleted`, `test_main_py_has_no_server_import`, `test_main_py_has_no_mcp_run_call`).
- Cleanup: removed empty `TestFromAC_ModuleStub` class after deleting all of its tests.
- Files changed: tests/test_mcp_memory_1267.py
- Commit: 67d56bff (`test: remove stale mcp-memory assertions (#1275, builder)`).
- Quality runner (scoped target): tests/test_mcp_memory_1267.py -> 6 passed, 0 failed; ruff clean.
- Quality runner (broader context): tests/test_mcp_memory_1266.py and tests/test_mcp_memory_1269.py run surfaced existing failures in #1266 consumer-drift/state-transition assertions; no failures in this task file.
- quality-runner env fallback: initial run had startup SIGINT/130; one mandated retry with explicit hint succeeded cleanly.

- Reflection:
  - Problem faced: stale assertions were coupled to deleted-file assumptions that no longer hold after epic follow-up work.
  - Workaround applied: removed only named stale tests and validated class integrity (no empty shells left).
  - Pattern discovered: file-existence assertions are brittle across refactors; broader invariant tests are more durable.
  - Time sink: transient quality-runner environment interruption required protocol retry.
  - Quality gap: sibling-task failures remain in 1266 scope and should be handled in that task stream.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped run: pytest 6 passed, 0 failed, 0 skipped on `tests/test_mcp_memory_1267.py`
- quality-runner contextual run: pytest 103 passed, 4 failed, 0 skipped on `tests/test_mcp_memory_1266.py`, `tests/test_mcp_memory_1269.py`, and `tests/test_memory_models_1268.py`
- Contextual failures are confined to `tests/test_mcp_memory_1269.py::TestFromAC_TimestampValidation::{test_created_at_date_only_rejected,test_updated_at_date_only_rejected,test_created_at_timezone_naive_rejected,test_updated_at_timezone_naive_rejected}` at lines 168, 176, 184, and 192. Task #1269 is still `in-progress`, and its body already documents these as its own outstanding RED/FAIL scope rather than a regression introduced by #1275.

### Lint
- ruff clean on `tests/test_mcp_memory_1267.py`

### Coverage
- Skipped per td:0 mechanical cleanup workflow.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- td:0 task: TestFromAC audit and coverage gates are skipped by workflow.
- Builder modified a `TestFromAC_*` file only because this task's AC explicitly requires removing four stale assertions and the architect marked the task `td:0` with `Test-writer: SKIP`. Review verified exact named removals only.

#### Security Review
- No security issues found. Scope is a single Python test file.

#### Test Integrity
- Current file contains only the surviving guards at `tests/test_mcp_memory_1267.py:26`, `:35`, `:45`, `:55`, `:61`, and `:71`.
- No empty class shell remains: the file now defines only `TestFromAC_NoSQLiteImports` (`:23`), `TestFromAC_NoMigrationScripts` (`:42`), `TestFromAC_LegacyTestFilesRemoved` (`:52`), and `TestFromAC_TestDirEmpty` (`:68`).
- Removed targets are absent from the live file: `test_server_py_deleted`, `test_tools_py_deleted`, `test_main_py_has_no_server_import`, and `test_main_py_has_no_mcp_run_call`.

#### Test Quality
- ADEQUATE for td:0 cleanup. The remaining guards still prove the intended invariants without relying on deleted-file assumptions for recreated runtime files.
- Redundancy rationale confirmed in live source: `serve/mcp-memory/src/owlbear_mcp_memory/server.py:72` and `:76-140` define the FastMCP server/tool registrations; `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:93-186` provides markdown-backed tool implementations; `serve/mcp-memory/src/owlbear_mcp_memory/__main__.py:5` and `:8` restore the entry point.

#### Data Safety
- No data-safety issues found in task scope.

#### Implementation-Aware Gaps
- None in #1275 scope.
- Adjacent failures remain in task #1269's timestamp-validation suite and are unrelated to this deletion-only change.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section and no prior `## Review Evidence` section on #1275.
- Builder commit presence confirmed in `.git/logs/HEAD:1511` and `.git/logs/refs/heads/dev:1377` for `67d56bffba208481be1cb19659f3c29bb20be9f1` (`test: remove stale mcp-memory assertions (#1275, builder)`).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Remove the four stale test functions (`test_server_py_deleted`, `test_tools_py_deleted`, `test_main_py_has_no_server_import`, `test_main_py_has_no_mcp_run_call`) | Live file no longer contains the four named stale tests; surviving tests are only at `tests/test_mcp_memory_1267.py:26`, `:35`, `:45`, `:55`, `:61`, `:71` | structural file inspection | PASS |
| If removing all tests from a class leaves it empty, remove the empty class too | Live file defines only four non-empty classes at `tests/test_mcp_memory_1267.py:23`, `:42`, `:52`, `:68`; no `TestFromAC_ModuleStub` remains | structural file inspection | PASS |
| `uv run pytest tests/test_mcp_memory_1267.py` passes | quality-runner scoped run: 6 passed, 0 failed | `tests/test_mcp_memory_1267.py` | PASS |
| No other test files regress | Contextual run failures are confined to separate in-progress task #1269 timestamp tests (`tests/test_mcp_memory_1269.py:168`, `:176`, `:184`, `:192`); no failures in the changed file and no evidence of a task-caused regression | `tests/test_mcp_memory_1266.py`, `tests/test_mcp_memory_1269.py`, `tests/test_memory_models_1268.py` | PASS |

### Deductions
- -0.03 diff-level immutability of the task test file cannot be proven fully without a direct commit diff
- -0.03 non-regression assessment relies on contextual neighboring-suite evidence rather than a pre-change baseline snapshot
- Confidence: 0.94

### Verdict
- PASS -> docs
- Confidence: 0.94

### Action
- Advance to docs.
[[2026-05-02]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Only file changed is `tests/test_mcp_memory_1267.py` — test-only removal, no behavior/API/CLI/config change |
| 2 | Module docstrings | No | N/A | No production Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research phase for this td:0 cleanup task |
| 5 | Diagram maintenance (describes match) | No | N/A | No diagram describes test files |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram request in task body |
| 7 | Deletion detection | No | N/A | Four test functions deleted from a test file — not an IN-scope descriptive doc; no orphaned IN-scope docs reference these stale tests |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| tests/test_mcp_memory_1267.py | OUT | N/A — test file |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1275-*` files found)
[[2026-05-02]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Remove four stale test functions | File read confirms `test_server_py_deleted`, `test_tools_py_deleted`, `test_main_py_has_no_server_import`, `test_main_py_has_no_mcp_run_call` absent from `tests/test_mcp_memory_1267.py` | PASS |
| Remove empty class if applicable | No `TestFromAC_ModuleStub` in file; 4 non-empty classes remain at L23, L42, L52, L68 | PASS |
| `uv run pytest tests/test_mcp_memory_1267.py` passes | Reviewer scoped run: 6 passed, 0 failed; full-suite confirms no failure in this file | PASS |
| No other test files regress | Full suite 126 failures all in unrelated modules (decisions_1195, mcp_kanban_1196, engine_init_1068, cockpit_react_compiler_1015); none attributable to #1275 | PASS |

### Test Results
- pytest (full): 3611 passed, 126 failed (all pre-existing in other task streams), 4 skipped
- ruff: 3 violations in unrelated modules; task file clean

### Architect Quality: 5/5
Specific named targets, correct rationale for removal vs update, appropriate td:0 classification, clean implementation path.

### Deduction Breakdown
- No AC lines without evidence: 0
- No lint violations in scope: 0
- AC quality > 3: 0
- Reviewer evidence present and detailed: 0
- No full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive