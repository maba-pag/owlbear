---
id: 675
title: Add per-package tests for mcp-memory server
status: archived
priority: medium
created: 2026-04-08T18:14:33.571087+02:00
updated: 2026-04-09T03:59:01.2969341+02:00
started: 2026-04-09T03:59:01.2969341+02:00
completed: 2026-04-09T03:59:01.2969341+02:00
tags:
    - scope:mcp-memory
    - ' type:test'
    - ' source:analysis'
depends_on:
    - 674
class: standard
---

## Context

Analysis synthesis identified that `serve/mcp-memory/` has zero per-package tests — no `tests/` directory exists. This is the only MCP server without local tests. The memory server contains the most self-contained logic of any server (approval state machine, scope-tiered sorting, confidence validation, and curator integration).

Root test files (`test_approve_memory_531.py`, `test_approve_memory_585.py`) exist but reference stale `packages/` paths (being fixed in #674).

## Acceptance Criteria

- [ ] AC1: `serve/mcp-memory/tests/` directory exists with `__init__.py` and at least 1 test file (pattern: mcp-kanban, mcp-knowledge, mcp-project all use `__init__.py`, not `conftest.py`)
- [ ] AC2: Approval state machine tested — all 3 valid transitions (`pending→approved`, `pending→deleted`, `deleted→pending`) and rejection of invalid transitions
- [ ] AC3: `record_learning` validation tested — confidence below 0.7 returns error, invalid category returns error
- [ ] AC4: `get_knowledge` scope-tiered sort order tested — tier 1 (agent+project) before tier 4 (global)
- [ ] AC5: `mark_for_deletion` idempotency tested — calling twice on same entry succeeds
- [ ] AC6: `list_entries` filter combinations tested — by agent_id, category, status, include_deleted
- [ ] AC7: Package smoke test — `import owlbear_mcp_memory` succeeds

Depends on: #674 (stale path fixes)

[[2026-04-08]] Wed 23:52
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One package, one test suite |
| Interface clarity | PASS | AC2-AC7 are specific testable conditions; AC1 refined to match pattern |
| Dependency correctness | PASS | #674 is done |
| Module layering | PASS | Tests within package boundary |
| TDD compliance | PASS | This IS the test task (type:test) |
| KISS/YAGNI | PASS | Minimal scope, follows established pattern |
| Premise challenge | PASS | mcp-kanban, mcp-knowledge, mcp-project all have per-package tests; mcp-memory is the only gap |
| Pattern consistency | PASS | AC1 refined from conftest.py to __init__.py to match all 3 existing per-package test dirs |
| Security surface | N/A | Tests only |
| Single domain | PASS | mcp-memory domain only |

### AC Refinement Applied

- **AC1:** Changed `conftest.py` to `__init__.py` — all 3 existing MCP server per-package test directories (mcp-kanban/tests/, mcp-knowledge/tests/, mcp-project/tests/) use `__init__.py`, none use `conftest.py`. Shared fixtures should be defined inline per the established pattern.

### Builder Guidance

- AC2-AC7 overlap with existing root-level tests (test_memory_tools_556.py, test_set_approval_state_569.py, test_scaffold_mcp_memory_524.py). Per-package tests should be focused unit tests exercising the package's public API, complementing (not duplicating) root tests.
- Use in-memory SQLite (`:memory:`) for all tests — matches root test pattern and avoids disk side effects.
- Reference helper patterns from test_memory_tools_556.py: `_make_conn()` and `_make_app_ctx()` factories.
- Follow mcp-kanban/tests/ structure: test_package.py (smoke), test_server.py (tools unit tests).

### Codebase Evidence

- `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` — all 5 tool functions to test: get_knowledge, record_learning, list_entries, mark_for_deletion, set_approval_state
- `serve/mcp-memory/src/owlbear_mcp_memory/models.py` — MemoryEntry model with `_VALID_CATEGORIES` and approval_state Literal
- `serve/mcp-memory/src/owlbear_mcp_memory/server.py` — AppContext, `_VALID_TRANSITIONS` frozenset in tools.py

### Challenge Results

- Challenger: FALLBACK — subagent returned no output
- Architect response: Proceeded with own evaluation; AC is sound after AC1 refinement

### Verdict: APPROVE (with AC1 refinement)
### Action Taken: Refined AC1 (conftest.py → __init__.py to match codebase pattern), advanced to todo

[[2026-04-09]] Thu 00:40
## Test-Writer Notes
- Test files: `serve/mcp-memory/tests/__init__.py`, `serve/mcp-memory/tests/test_package.py`, `serve/mcp-memory/tests/test_server.py`
- Pattern: follows mcp-kanban/tests/ structure (`__init__.py` + `test_package.py` + `test_server.py`)
- Classes: `TestFromAC_ApprovalStateMachine`, `TestFromAC_RecordLearningValidation`, `TestFromAC_GetKnowledgeSortOrder`, `TestFromAC_MarkForDeletion`, `TestFromAC_ListEntriesFilters`
- Tests per category: happy 13, edge 3, error 7, boundary 1
- Total: 24 tests, all PASS (type:test task — implementation pre-exists; tests verify existing contract)
- ruff: clean
- Commit: `90a44ac` — test: add per-package tests for mcp-memory server (#675, test-writer)
- AC coverage: AC1 ✓ (directory + __init__.py + test files), AC2 ✓ (7 tests: 3 valid transitions + 3 invalid + nonexistent raises ToolError), AC3 ✓ (4 tests: confidence < 0.7, confidence 0.0, invalid category, boundary 0.7), AC4 ✓ (2 tests: tier sort + deleted exclusion), AC5 ✓ (3 tests: first call, second call no-op, nonexistent raises ToolError), AC6 ✓ (7 tests: agent_id, category, status, deleted default, include_deleted, AND combo, no filters), AC7 ✓ (1 smoke test)

[[2026-04-09]] Thu 01:30
## Builder Notes

### Files Changed
- None — type:test task, implementation pre-existed. Test-writer commit `90a44ac` added all test files.

### Test Results
- **24 passed**, 0 failed
- Test files: `serve/mcp-memory/tests/test_package.py` (1 test), `serve/mcp-memory/tests/test_server.py` (23 tests)
- Run: `uv run python -m pytest serve/mcp-memory/tests/ -v`

### Coverage
- `tools.py`: 90% (145 stmts, 15 missed — uncovered: optional `categories`/`min_confidence` branches in `get_knowledge` and `_apply_tool_exclusions` env-var init; neither in AC scope)
- Missed lines: 79–81, 83–84, 334–343

### Lint
- `ruff check serve/mcp-memory/tests/` → All checks passed ✓

### AC Evidence
- AC1 ✓ — `serve/mcp-memory/tests/__init__.py` + 2 test files (matches mcp-kanban pattern)
- AC2 ✓ — 7 tests: 3 valid transitions (`pending→approved`, `pending→deleted`, `deleted→pending`) + 3 invalid + nonexistent raises ToolError
- AC3 ✓ — 4 tests: confidence < 0.7, confidence 0.0, invalid category, boundary 0.7 passes
- AC4 ✓ — 2 tests: tier-1 (agent+project scope) precedes tier-4 (global), deleted excluded
- AC5 ✓ — 3 tests: first call marks deleted, second call no-op, nonexistent raises ToolError
- AC6 ✓ — 7 tests: filter by agent_id, category, status, deleted default, include_deleted, AND combo, no filters
- AC7 ✓ — smoke test: `import owlbear_mcp_memory` succeeds

### Notes
- VS Code test panel showed false failures (xdist workers crash in VS Code runner); `python -m pytest` ran cleanly with 10 workers
- No code changes required — builder verified correctness only

[[2026-04-09]] Thu 02:06
## Review Evidence

### Test Results (independent run)
pytest: **24 passed, 0 failed** — `serve/mcp-memory/tests/test_package.py` (1 test), `serve/mcp-memory/tests/test_server.py` (23 tests)
ruff: **clean** — 0 violations in `serve/mcp-memory/tests/` and `serve/mcp-memory/src/`

### Coverage
| Module | Coverage |
|--------|----------|
| `tools.py` | **90%** (145 stmts, 15 missed) |
| `__init__.py` | 100% |
| `server.py` | 54% (startup/lifecycle only — not in AC scope) |
| `approve.py` | 0% (not in AC scope) |
| `migrate.py` | 0% (not in AC scope) |
| `models.py` | 0% (not in AC scope) |

Uncovered lines in tools.py confirmed out-of-scope: lines 79–81, 83–84 (optional `categories`/`min_confidence` params), lines 334–343 (env-var exclusion init).

### AC Compliance Table

| AC | Mapped TestFromAC | Would Fail If Violated? | Verdict |
|----|-------------------|------------------------|---------|
| AC1: `tests/` + `__init__.py` + file | N/A (structural) | Yes — directory & import verified | COVERED |
| AC2: 3 valid transitions + invalid rejection | `TestFromAC_ApprovalStateMachine` (7 tests) | Yes — valid transitions assert DB row state; invalid check `result.startswith("error:")` | COVERED |
| AC3: confidence < 0.7 and invalid category | `TestFromAC_RecordLearningValidation` (4 tests) | Yes — error tests check `"error:"` prefix; boundary test calls `uuid.UUID(result)` which raises if result is an error string | COVERED |
| AC4: tier-1 before tier-4 sort | `TestFromAC_GetKnowledgeSortOrder` (2 tests) | Yes — `contents.index("specific") < contents.index("global")` assertion directly targets sort order | COVERED |
| AC5: idempotency on 2nd call | `TestFromAC_MarkForDeletion` (3 tests) | Yes — 2nd call asserts `not second_result.startswith("error:")` | COVERED |
| AC6: filter combinations | `TestFromAC_ListEntriesFilters` (7 tests) | Yes — each filter verified with in/not-in assertions; AND combo asserts exact `["match"]` result | COVERED |
| AC7: package importable | `test_mcp_memory_package_importable` | Yes — checks `__name__` attribute | COVERED |

### Security Review
- No new production code (type:test task) — builder changed nothing
- Test code reviewed: parameterized SQLite queries confirmed by code-reader; no string interpolation of user values
- No hardcoded secrets, no injection, no path traversal, no insecure deserialization
- No new dependencies

### TestFromAC Integrity
Builder notes: "Files Changed: None." Test files introduced by test-writer commit `90a44ac` only. No TestFromAC modifications by builder. All 5 `TestFromAC_*` classes match test-writer notes exactly.

### Deductions
- None

### Verdict
- 0 deductions • confidence: **.96 → PASS**
- Move: review → docs

[[2026-04-09]] Thu 02:36
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | type:test task — only test files added (`serve/mcp-memory/tests/`); no production code modified; no API or convention change |
| 2 | Module docstrings | No | N/A | No src modules created or modified; test_server.py already carries accurate module docstring describing AC coverage |
| 3 | External attribution | No | N/A | Follows internal mcp-kanban/tests/ pattern; no external repos or articles used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | `mcp-memory-scaffold-validation.md` belongs to #524; no research doc produced for this task |

### Files Updated
None — no docs impact.

### Scratch Files
None found matching `.owlbear/scratch/675-*`.

[[2026-04-09]] Thu 03:59
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `tests/` + `__init__.py` + test files | `serve/mcp-memory/tests/` contains `__init__.py`, `test_package.py`, `test_server.py` — matches mcp-kanban pattern | PASS |
| AC2: Approval state machine (3 valid + invalid rejection) | `TestFromAC_ApprovalStateMachine` — 7 tests: pending→approved, pending→deleted, deleted→pending, approved→pending rejected, approved→deleted rejected, same-state rejected, nonexistent raises ToolError | PASS |
| AC3: record_learning validation | `TestFromAC_RecordLearningValidation` — 4 tests: confidence 0.69 error, confidence 0.0 error, invalid category error, boundary 0.7 succeeds | PASS |
| AC4: get_knowledge sort order | `TestFromAC_GetKnowledgeSortOrder` — 2 tests: tier-1 (agent+project) before tier-4 (global) via `contents.index()`, deleted excluded | PASS |
| AC5: mark_for_deletion idempotency | `TestFromAC_MarkForDeletion` — 3 tests: first call marks deleted, second call no-op, nonexistent raises ToolError | PASS |
| AC6: list_entries filters | `TestFromAC_ListEntriesFilters` — 7 tests: agent_id, category, status, deleted default, include_deleted, AND combo, no filters | PASS |
| AC7: package importable | `test_mcp_memory_package_importable` — asserts `__name__` attribute | PASS |

### Test Results
- pytest (per-package): 24 passed, 0 failed
- pytest (full suite): 3667 passed, 394 failed, 18 skipped, 1 error — all failures pre-existing, none in task scope
- ruff (mcp-memory scope): All checks passed

### Reviewer Evidence
Present, detailed, PASS at .96. AC compliance table with test assertions, security review, TestFromAC integrity check. Trusted.

### Architect Quality: 4/5
AC lines are specific and testable. AC1 was proactively refined by architect (conftest.py → __init__.py to match codebase pattern). Builder guidance (in-memory SQLite, helper patterns, structure reference) was relevant. Minor gap: AC could have specified the 3 invalid transitions explicitly rather than just "rejection of invalid transitions."

### Deduction Breakdown
- AC lines without evidence: 0 (all 7 verified) → 0
- Lint violations: 0 in scope → 0
- AC quality ≤ 3: no (score 4) → 0
- Missing reviewer section: no → 0
- Full-suite failures in task scope: 0 → 0
- Total deductions: 0

### Confidence: .98
### Action: archive
