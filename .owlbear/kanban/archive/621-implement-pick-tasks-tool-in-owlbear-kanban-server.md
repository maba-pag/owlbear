---
id: 621
title: Implement pick_tasks tool in owlbear-kanban server
status: archived
priority: medium
created: 2026-04-05T01:31:03.9704718+02:00
updated: 2026-04-05T18:14:16.2703649+02:00
started: 2026-04-05T18:14:16.2703649+02:00
completed: 2026-04-05T18:14:16.2703649+02:00
tags:
    - scope:mcp
    - phase-2
    - type:build
parent: 619
depends_on:
    - 620
class: standard
---

## Acceptance Criteria

- New `pick_tasks` tool registered in owlbear-kanban MCP server (server.py)
- Tool signature: `pick_tasks(limit: int = 25) → dict`
- No filters — zero-config, opinionated about what's eligible
- Gate logic migrated from serve/orchestrator/src/owlbear/planner/gates.py:
  - check_atomicity: word-boundary "and" in title
  - check_tdd: in-progress tasks must have "## Test-Writer Notes"
  - check_clarity: active statuses must have bullet/numbered AC
- Sort logic migrated from serve/orchestrator/src/owlbear/planner/selector.py:
  - PRIORITY_RANK and STATUS_RANK sort keys
  - Cap at limit parameter
- Board reading uses existing _run_kanban with --unblocked --not-blocked --unclaimed flags
- Return format: `{"dispatch": [{"task_id": int, "status": str}]}`
- No agent mapping — orchestrator's responsibility
- No crash_failures — orchestrator's responsibility
- All tests from #620 pass
- Tool added to __all__ in server.py

[[2026-04-05]] Sun 10:39
## Research
- Research doc: .owlbear/research/pick-tasks-implementation.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Inline gates in server.py, raw-dict approach (confidence: .85)
- Follow-up tasks created: none (subtasks #620–#624 already exist)
- Decision requests: none

## Challenge Results
- Challenger: N/A — T1 implementation task, architecture decided in #619
- Tier: T1 (autonomous) — no new capabilities beyond approved #619 design

## Key Findings for Builder
- mcp-kanban has NO dep on orchestrator; gates must be copied+adapted, not imported
- list_tasks strips body — pick_tasks needs its own _run_kanban call with full JSON
- Body is str|None in KanbanTask — use task.get("body") or "" in gates
- Gate functions work on raw dicts (not Pydantic models) — matches list_tasks pattern
- Sort: (PRIORITY_RANK, STATUS_RANK) ascending, cap at limit (default 25)
- STATUS_AGENT_MAP and crash_failures NOT migrated — orchestrator responsibility
- Return: {"dispatch": [{"task_id": int, "status": str}]}
- Error: ToolError on rc!=0 or JSON parse failure; empty dispatch on all-gates-fail

[[2026-04-05]] Sun 11:56
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One tool (pick_tasks) with one purpose: select eligible tasks from board |
| Interface clarity | PASS | Input: limit:int=25. Output: {"dispatch":[{task_id,status}]}. Three gates enumerated with source. Sort keys specified. Board flags explicit |
| Dependency correctness | PASS | depends_on [620] (TDD RED test task, currently todo). #628 (tag param) depends ON #621, not the reverse |
| Module layering | PASS | mcp-kanban has no dep on orchestrator. Gates copied+adapted, not imported. Uses _run_kanban same as all tools |
| TDD compliance | PASS | #620 is the preceding test task, #621 depends on it |
| KISS/YAGNI | PASS | No tag param (that is #628), no agent mapping, no crash_failures |
| Premise challenge | PASS | Migrating deterministic logic from agent subagent to MCP tool |
| Pattern consistency | PASS | Follows list_tasks raw-dict pattern, _run_kanban, ToolError, ToolAnnotations(readOnly, idempotent) |
| Security surface | PASS | No new system boundaries. limit:int validated by Pydantic |
| Single domain | PASS | scope:mcp only, all changes within mcp-kanban server |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| _run_kanban (list) | rc != 0 | ToolError | Yes (AC) | Error to caller |
| JSON parse | malformed stdout | ToolError | Yes (AC) | Error to caller |
| All gates fail | no tasks pass | None | Yes (empty dispatch) | Empty result |
| Body is None | null in gate | AttributeError | Yes (Key Findings) | N/A if guarded |

### Codebase Evidence
- board.py L43-48: --unblocked --not-blocked --unclaimed are valid kanban-md flags
- h-kanban-md SKILL: --unblocked vs --not-blocked are orthogonal
- list_tasks does NOT expose --unblocked; pick_tasks constructs own _run_kanban args
- selector.py DISPATCH_CAP=20 but #621/#619 intentionally set default limit=25
- gates.py Task model has body:str but raw dict may have null; Key Findings addresses this

### AC Notes
- #628 tag param: dependency graph has #628 depends_on [621]; incremental build follows KISS/YAGNI
- Builder should add ToolAnnotations(readOnlyHint=True, idempotentHint=True) and outputSchema patch
- Builder may add _patch_params for limit description

### Challenge Results
- Challenger: FALLBACK, challenger agent not in workspace agent roster
- Architect response: Proceed, T1 implementation, architecture pre-decided in #619

### Verdict: APPROVE
### Action: backlog to todo

[[2026-04-05]] Sun 13:47
## Test-Writer Notes
- Test file: `tests/test_pick_tasks_621.py`
- Class: `TestFromAC_PickTasksNullBodySafety` (6 tests)
- Total: 6 tests, all FAIL
- Ruff: clean
- Failure mode: `TypeError: expected string or bytes-like object, got 'NoneType'` in `_check_pick_gates` — `task.get("body", "")` returns `None` when the key exists with a `null` value; Key Findings for #621 specified `task.get("body") or ""` but the implementation uses `task.get("body", "")` instead
- AC coverage: "#621 Key Findings — null body safety" (pre-existing tests from #620 cover all other AC items; implementation was pre-delivered via #620 GREEN phase; 33/33 tests in test_pick_tasks_620.py PASS)
- Categories: error paths (TypeError from TDD gate, clarity gate), edge (mixed null/valid board)
- Note: all original #620 tests PASS — test_pick_tasks_621.py adds null-body regression suite for the gap left by `task.get("body", "")` vs `task.get("body") or ""`

[[2026-04-05]] Sun 13:50
## Builder Notes
- **File changed:** `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — 1 line, `_check_pick_gates`
- **Fix:** `task.get("body", "")` → `task.get("body") or ""` (line 541) — handles `"body": null` in raw JSON where `.get(key, default)` returns None instead of the default
- **RED verified:** 6/6 tests FAILED before fix (TypeError: expected string or bytes-like object, got 'NoneType')
- **GREEN verified:** 6/6 tests PASS after fix; 33/33 #620 tests still PASS (39 total)
- **Ruff:** clean
- **Coverage:** `_check_pick_gates` and `pick_tasks` lines fully covered; no missing lines in 537-570 range

[[2026-04-05]] Sun 16:21
## Review Evidence

### Changed Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — 1-line fix (`task.get("body", "")` → `task.get("body") or ""`), plus `import re`, `pick_tasks` in `__all__`, gate constants, `_check_pick_gates()`, and `@mcp.tool pick_tasks()` (bulk implementation from #620 GREEN phase)

### Tests (independently run)
`uv run pytest tests/test_pick_tasks_621.py tests/test_pick_tasks_620.py -v`: **39 passed, 0 failed**
- `TestFromAC_PickTasksNullBodySafety` (6 tests): 6/6 PASS
- `TestFromAC_PickTasksSignature` (3), `BasicPick` (5), `GateFiltering` (8), `Limit` (4), `SortOrder` (3), `EdgeCases` (4), `BoardFlags` (6): 33/33 PASS

### Lint
`ruff check serve/mcp-kanban/src/owlbear_mcp_kanban/server.py tests/test_pick_tasks_620.py tests/test_pick_tasks_621.py`: **All checks passed!**

### Coverage
Lines 506–570 (pick_tasks block + `_check_pick_gates`) absent from missing list. Builder claim confirmed — `_check_pick_gates` and `pick_tasks` fully covered by the 39-test suite.

### Pass 1 — CRITICAL

#### AC Compliance

| AC Line | Mapped Test(s) | Would Fail If Violated? | Verdict |
|---------|----------------|------------------------|---------|
| pick_tasks registered in server.py | Import + all 39 tests | Yes — ImportError | COVERED |
| Signature `pick_tasks(limit:int=25)→dict` | test_has_limit_parameter, test_default_limit_is_25 | Yes | COVERED |
| Gate: check_atomicity (word-boundary "and") | test_atomicity_gate_excludes_and_in_title, test_atomicity_gate_passes_word_boundary_false_positive | Yes | COVERED |
| Gate: check_tdd (in-progress must have ## Test-Writer Notes) | test_tdd_gate_excludes_in_progress_without_*, test_tdd_gate_passes_* | Yes | COVERED |
| Gate: check_clarity (active statuses must have bullet/numbered AC) | test_clarity_gate_excludes_todo_without_bullet_ac, 3 passing tests | Yes | COVERED |
| Sort: (PRIORITY_RANK, STATUS_RANK) ascending, cap at limit | TestFromAC_PickTasksSortOrder (3), TestFromAC_PickTasksLimit (4) | Yes | COVERED |
| Board: --unblocked --not-blocked --unclaimed flags | test_passes_unblocked_flag, test_passes_not_blocked_flag, test_passes_unclaimed_flag | Yes | COVERED |
| Return format: {"dispatch": [{"task_id": int, "status": str}]} | test_dispatch_entries_have_task_id_and_status, test_dispatch_entry_has_only_task_id_and_status | Yes | COVERED |
| ToolError on rc!=0 or JSON parse failure | test_nonzero_rc_raises_tool_error, test_malformed_json_raises_tool_error | Yes | COVERED |
| Tool added to __all__ | Confirmed in diff; no dedicated test (passes entire import chain) | N/A | COVERED |
| All tests from #620 pass | 33/33 pass (independently verified) | Yes | COVERED |
| Key Findings null-body safety: task.get("body") or "" | TestFromAC_PickTasksNullBodySafety (6 tests) — crash absence + gate behavior | Yes — TypeError or wrong gate result | COVERED |

#### Security
- `_run_kanban` uses list args — no shell injection
- `json.loads()` — safe deserialization
- `limit: int` validated by Pydantic/FastMCP
- No new dependencies, no secrets, no path traversal
- PASS

#### TestFromAC Integrity

| Test Class | Change Made | Assessment |
|------------|-------------|------------|
| TestFromAC_PickTasksNullBodySafety (6 tests) | None — exactly as written by test-writer | PRESERVED |
| All 33 TestFromAC_* from #620 | None | PRESERVED |

#### Test Quality
- **Assertion specificity:** STRONG — value-level assertions throughout (task_id==42, len==5, X not in ids, set(keys)=={"task_id","status"}, TypeError raised). No-raise tests use `assert "dispatch" in result` (appropriate for crash-safety intent — would fail with TypeError on revert).
- **Error-path coverage:** STRONG — null-body crash path, gate-fail path, rc!=0, malformed JSON all covered.
- **Mutation resistance:** STRONG — each gate branch, each flag, each boundary individually tested.
- **Test independence:** STRONG — each test patches `_run_kanban` independently.
- **Descriptive names:** STRONG.

#### Data Safety: No issues.

### Deductions
None.

### Confidence: .95 → PASS

[[2026-04-05]] Sun 16:28
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `pick_tasks` is a new MCP tool. `.github/copilot-instructions.md` is 5-line identity-only file (no tool inventory). `h-mcp-kanban` skill already includes `pick_tasks` as tool #8 — accurate count of 8 tools. No update needed. |
| 2 | Module docstrings | Yes | Verified | `_check_pick_gates`: `"""Return True if task passes atomicity, TDD, and clarity gates."""` ✓ `pick_tasks`: `"""Pick dispatchable tasks: gate-filtered, sorted by priority/status, capped at limit."""` ✓ |
| 3 | External attribution | No | N/A | Research doc studied 8 sources — all internal project files (server.py, gates.py, selector.py, models.py, internal research docs, #619 task body). No external attribution required. |
| 4 | CLI changes | No | N/A | MCP tool only — no CLI command changes. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/pick-tasks-implementation.md` exists and is linked in task body. Follow-up tasks: "none (subtasks #620–#624 already exist)" ✓ |

### Files Updated
None — all items verified as accurate or not applicable.

### Scratch Files
None found matching `.owlbear/scratch/621-*`.

[[2026-04-05]] Sun 18:14
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| pick_tasks registered in server.py | server.py L51 __all__, 39 tests import it | PASS |
| Signature pick_tasks(limit:int=25)->dict | test_has_limit_parameter, test_default_limit_is_25 | PASS |
| Gate: check_atomicity (word-boundary "and") | test_atomicity_gate_excludes_and_in_title | PASS |
| Gate: check_tdd (in-progress + Test-Writer Notes) | test_tdd_gate_excludes_in_progress_without_test_writer_notes | PASS |
| Gate: check_clarity (bullet/numbered AC) | test_clarity_gate_excludes_todo_without_bullet_ac | PASS |
| Sort: (PRIORITY_RANK, STATUS_RANK), cap at limit | TestFromAC_PickTasksSortOrder (3), TestFromAC_PickTasksLimit (4) | PASS |
| Board: --unblocked --not-blocked --unclaimed | test_passes_unblocked_flag, test_passes_not_blocked_flag, test_passes_unclaimed_flag | PASS |
| Return format: {dispatch: [{task_id, status}]} | test_dispatch_entries_have_task_id_and_status | PASS |
| ToolError on rc!=0 / JSON parse failure | test_nonzero_rc_raises_tool_error, test_malformed_json_raises_tool_error | PASS |
| Tool in __all__ | server.py L51 confirmed | PASS |
| All #620 tests pass | 33/33 pass (independently verified) | PASS |
| Null-body safety: task.get("body") or "" | TestFromAC_PickTasksNullBodySafety (6/6 pass), server.py L541 | PASS |

### Test Results
- pytest (task-scoped): 39 passed, 0 failed
- pytest (full suite): 2881 passed, 444 failed, 18 skipped — 0 failures in #621 scope; all 444 from other tasks
- ruff: All checks passed

### Architect Quality: 4/5
Specific AC with exact tool name, signature, gates, sort keys, board flags, return format, error handling. Key Findings proactively identified null-body edge case.

### Deduction Breakdown
None. All 12 AC lines have evidence. Lint clean. Reviewer section present and detailed. No task-scope test failures.
Note: test_pick_tasks_621.py was uncommitted by test-writer; committed by auditor as leftover (a377cee).

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3fcb62c | feat | server.py (pick_tasks + gates) | #620 |
| a377cee | test+chore | test_pick_tasks_621.py, kanban board | #621 |
