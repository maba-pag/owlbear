---
id: 980
title: 'GREEN: edit_task + end_work guidance integration'
status: archived
priority: medium
created: 2026-04-18T21:18:27.029383+00:00
updated: 2026-04-19T14:03:40.464005+00:00
tags:
- scope:mcp
- scope:kanban
- type:build
parent: 973
depends_on:
- 978
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. GREEN phase. Makes #978 tests pass.

## Acceptance Criteria

File: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

- `edit_task` block branch: after engine call, invoke `collect_guidance("edit_block", before, after)` and attach to returned `KanbanTask.guidance`. Also remove `block:user` tag from task tags (agent re-blocking takes ownership per D3).
- `end_work` block path: invoke `collect_guidance("end_work_block", ...)`; remove `block:user` tag.
- `end_work` success path: invoke `collect_guidance("end_work_success", ...)`.
- All other paths return empty `guidance`.

All tests in #978 pass; all existing kanban MCP tests still pass.
[[2026-04-19]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single file, wiring guidance into edit_task + end_work |
| Interface clarity | REFINE | AC specifies legacy operation names; current API uses different pattern |
| Dependency correctness | PASS | #978 archived/done, tests exist |
| Module layering | PASS | Same-layer wiring, no upward imports |
| TDD compliance | PASS | RED tests in test_guidance_edit_task_973.py and test_guidance_end_work_973.py |
| KISS/YAGNI | PASS | Minimal wiring only |
| Premise challenge | PASS | Implementation appears already in place — builder verifies tests pass |
| Pattern consistency | REFINE | AC says "edit_block"/"end_work_block"/"end_work_success" but codebase uses "edit_task"/"end_work" with outcome kwarg (matching move_task pattern) |
| Security surface | PASS | No new external input handling |
| Single domain | PASS | MCP kanban domain only |

### Challenge Results

- Challenger: reconsider (0.55)
- Key concerns: (C1) implementation already exists, (C2) AC operation names mismatch, (C4/C5) suppress pattern risks
- Architect response: Accepted C2 — refining AC. C1 addressed with verification note. C4/C5 are pre-existing patterns in move_task — separate task if needed.

### Verdict: REFINE

### Action Taken: AC needs update — legacy operation names replaced with current API pattern; verification note added. Returning to backlog for re-approval after edit

[[2026-04-19]]

## AC Refinement (architect pass 2)

Rewrote AC to use canonical API pattern (matching `move_task` at server.py:227). Added verification note since implementation appears already present.

**Refined AC:**

File: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

- `edit_task`: after engine call, invoke `collect_guidance("edit_task", None, task)` and assign to `task.guidance`. When `block` or `unblock` params are set, also remove `block:user` from task tags (agent re-blocking takes ownership per D3).
- `end_work` block path (`outcome="block"`): invoke `collect_guidance("end_work", None, task, outcome=outcome)`. Remove `block:user` tag via separate `engine.edit_task` call before guidance collection.
- `end_work` success path (`outcome="success"`): same `collect_guidance("end_work", None, task, outcome=outcome)` call — function detects success via outcome kwarg.
- All other `end_work` outcomes (fail, reject) and non-blocking `edit_task` calls: `collect_guidance` returns empty list (no guidance applies).
- All guidance calls wrapped in `contextlib.suppress(Exception)` — guidance is advisory, never blocks tool success.

**Note:** Implementation may already be in place from prior work. Builder verifies all #978 tests pass and existing mcp-kanban tests remain green.

### Verdict: APPROVE → todo

[[2026-04-19]]

## Test-Writer Notes

- Test file: `serve/mcp-kanban/tests/test_guidance_server_980.py`
- Classes: `TestFromAC_GuidanceSuppressContract`, `TestFromAC_GuidanceCallWiring`, `TestFromAC_BlockUserTagOrderingInEndWork`
- Tests per category: happy 3 (wiring call signatures), edge 1 (ordering: block:user removed before guidance), error 2 (suppress: guidance exception doesn't propagate)
- Total: 6 tests
- ruff: clean

### Pre-implemented state — all tests PASS

The implementation in `server.py` was completed ahead of schedule (as the architect noted). All #978 tests (9) and all new #980 tests (6) pass. Tests cannot be made to fail because the contract they verify is fully implemented.

### AC Coverage

| AC line | Tests |
|---------|-------|
| `collect_guidance("edit_task", None, task)` called after engine call | `test_edit_task_calls_collect_guidance_with_edit_task_operation` |
| `collect_guidance("end_work", ..., outcome=outcome)` called | `test_end_work_success_calls_collect_guidance_with_outcome_kwarg`, `test_end_work_fail_calls_collect_guidance_with_outcome_kwarg` |
| All guidance calls wrapped in `contextlib.suppress(Exception)` | `test_edit_task_guidance_exception_suppressed`, `test_end_work_guidance_exception_suppressed` |
| block:user removed BEFORE guidance collection in end_work(block) | `test_end_work_block_with_block_user_tag_emits_dr_guidance` |

### Builder instruction

Verify all 15 tests (9 from #978 + 6 new) pass and existing mcp-kanban suite (66 tests total) remains green. No implementation work expected — implementation is already in place.
[[2026-04-19]]

## Builder Notes

- No implementation work required — implementation was already in place (per test-writer and architect notes).
- Files changed: none.
- Verified RED: per test-writer notes, tests were pre-passing (non-implementation pass-through).
- Test results: 9/9 from #978 (test_guidance_edit_task_973.py + test_guidance_end_work_973.py), 6/6 from #980 (test_guidance_server_980.py), full mcp-kanban suite 72/72 passed.
- Lint: ruff clean on serve/mcp-kanban/.
- Coverage: no new code paths introduced.
- Evidence: All AC lines verified by existing tests; collect_guidance wiring in server.py confirmed present and correct.
[[2026-04-19]]

## Review Evidence

### Tests

72 passed, 0 failed. pytest exit 0.

### Lint

ruff: clean. Exit 0.

### Coverage

`owlbear_mcp_kanban.server`: 64%. Pre-existing — builder changed no files. AC-relevant paths all exercised.

### AC Compliance

| AC Line | Tests | Would Fail If Violated? | Verdict |
|---------|-------|------------------------|---------|
| `edit_task`: `collect_guidance("edit_task", None, task)` after engine call | `test_edit_task_calls_collect_guidance_with_edit_task_operation` — `assert_called_once_with("edit_task", None, ANY)` | Yes | COVERED |
| `edit_task`: block/unblock removes `block:user` tag | `test_block_removes_block_user_tag_if_present`, `test_unblock_no_dr_guidance_and_removes_block_user_tag` | Yes | COVERED |
| `end_work` block path: `collect_guidance("end_work", None, task, outcome=outcome)` + `block:user` removed BEFORE | `test_end_work_block_with_block_user_tag_emits_dr_guidance` (integration — DR guidance present only if ordering correct) | Yes | COVERED |
| `end_work` success path: `collect_guidance("end_work", None, task, outcome="success")` | `test_end_work_success_calls_collect_guidance_with_outcome_kwarg` | Yes | COVERED |
| fail/reject/non-blocking → empty guidance | `test_end_work_fail_calls_collect_guidance_with_outcome_kwarg`, integration tests in #973 | Yes | COVERED |
| All guidance wrapped in `contextlib.suppress(Exception)` | `test_edit_task_guidance_exception_suppressed`, `test_end_work_guidance_exception_suppressed` — RuntimeError side_effect | Yes | COVERED |

### TestFromAC Integrity

No files changed by builder. All TestFromAC_* methods unmodified.

### Test Quality: STRONG

Suppress tests force real exceptions, verify both return and guidance=[]. Wiring tests use assert_called_once_with with explicit op strings and outcome kwarg. Ordering test detects sequence inversion via guidance content difference.

### Security: CLEAN

No new external input. suppress(Exception) intentional and tested.

### Builder Process: CLEAN — single pass, pre-existing implementation

### Informational (non-blocking)

- Docstring in test_guidance_edit_task_973.py references task #985; file named 973 — minor comment inconsistency.
- 64% module coverage pre-existing, not introduced here.

### Deductions: 0

**Confidence: .93 → PASS**
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Builder changed no files; guidance wiring pre-existing. copilot-instructions.md covers Cockpit API only — no kanban MCP tool internals documented there |
| 2 | Module docstrings | No | N/A | No files modified by builder; existing docstrings on edit_task and end_work accurate |
| 3 | External attribution | No | N/A | No external patterns referenced |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research doc produced or referenced |

### Files Updated

None — no docs impact.

### Scratch Files

None found for task #980.

### Verdict

No docs impact. All five checklist items N/A with evidence. Advancing to done.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `edit_task`: `collect_guidance("edit_task", None, task)` after engine call | server.py:303-304, test_edit_task_calls_collect_guidance_with_edit_task_operation | PASS |
| `edit_task`: block/unblock removes `block:user` tag | test_block_removes_block_user_tag_if_present, test_unblock_no_dr_guidance_and_removes_block_user_tag | PASS |
| `end_work` block path: guidance call + `block:user` removed before | server.py:338-342, test_end_work_block_with_block_user_tag_emits_dr_guidance | PASS |
| `end_work` success path: `collect_guidance("end_work", ..., outcome=outcome)` | server.py:341-342, test_end_work_success_calls_collect_guidance_with_outcome_kwarg | PASS |
| fail/reject/non-blocking: empty guidance | test_end_work_fail_calls_collect_guidance_with_outcome_kwarg, integration tests | PASS |
| All guidance wrapped in `contextlib.suppress(Exception)` | test_edit_task_guidance_exception_suppressed, test_end_work_guidance_exception_suppressed | PASS |

### Test Results

- pytest: 664 passed, 28 failed (all failures outside task scope: cockpit launch 21, knowledge schema/search 7). mcp-kanban: 72/72 green.
- ruff: clean

### Architect Quality: 4/5

Initial AC used legacy operation names; challenger flagged it. Architect rewrote in pass 2 with canonical API patterns matching move_task. Final AC specific and testable. Minor deduction for needing two passes, but quality process worked as designed.

### Deduction Breakdown

- AC lines without evidence: 0 (all 6 mapped to tests and spot-checked)
- Lint violations: 0
- AC quality <=3: N/A (score 4)
- Missing reviewer evidence: N/A (present, detailed, PASS)
- Full-suite failures in task scope: 0

### Confidence: 1.00

### Action: archive
