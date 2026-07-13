---
id: 981
title: 'GREEN: move_task guidance + pre-read'
status: archived
priority: medium
created: 2026-04-18T21:18:27.039443+00:00
updated: 2026-04-19T14:14:27.536453+00:00
tags:
- scope:mcp
- scope:kanban
- type:build
parent: 973
depends_on:
- 979
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. GREEN phase. Makes #979 tests pass.

## Acceptance Criteria

File: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

Per D6:

- `move_task` pre-reads current task via `_show_validated()` to capture `before.status`.
- After engine `move_task` call, invoke `collect_guidance("move", before, after)`.
- Attach result to returned `KanbanTask.guidance`.
- Status ordering pulled from `engine.board_config().statuses` (expose publicly if not already).
- Archived status excluded from skip detection.

All tests in #979 pass; all existing kanban MCP tests still pass.

## Note

If `engine.board_config()` is not currently public, expose it as a property/method (no breaking changes). Document in commit message.
[[2026-04-19]]

## Architecture Review

### Premise Challenge — DUPLICATE / Already Implemented

Every AC line is already satisfied in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (move_task, lines ~215-230):

| AC Line | Evidence | Status |
|---------|----------|--------|
| `move_task` pre-reads via `_show_validated()` | `pre_task = await _show_validated(app_ctx, task_id)` | ✅ Done |
| After engine call, invoke `collect_guidance("move", before, after)` | `collect_guidance("move", before=pre_task, after=result, status_names=status_names)` | ✅ Done |
| Attach result to `KanbanTask.guidance` | `result.guidance = collect_guidance(...)` | ✅ Done |
| Status ordering from `engine.board_config().statuses` | `[s["name"] for s in app_ctx.engine.board_config().statuses]` | ✅ Done |
| Archived excluded from skip detection | Archived not in config statuses list; `_move_guidance` returns `[]` on `ValueError` | ✅ Done |

`board_config()` is already public (engine.py line 303).

RED tests from #979 exist at `serve/mcp-kanban/tests/test_guidance_move_task_973.py`.

**Root cause:** Sibling task #991 ("Wire guidance into `move_task` with forward-skip detection") completed and archived the identical work. Task #981 was not cleaned up when #991 was resolved.

### Verdict: REJECT

### Action Taken: Moved to research. Recommend archiving as duplicate of #991 — no further work needed

[[2026-04-19]]

## Research

**Verdict: DUPLICATE — no work needed.**

Verified all 5 AC lines against current codebase:

| AC Line | File | Status |
|---------|------|--------|
| `move_task` pre-reads via `_show_validated()` | server.py L216 | ✅ |
| Invokes `collect_guidance("move", before, after)` | server.py L222 | ✅ |
| Attaches result to `KanbanTask.guidance` | server.py L222 | ✅ |
| Status ordering from `engine.board_config().statuses` | server.py L221 | ✅ |
| Archived excluded from skip detection | guidance.py `_move_guidance` ValueError catch | ✅ |

`engine.board_config()` is already public (engine.py L303).

All 11 related tests pass (5 in `test_guidance_move_task_973.py`, 6 in `test_guidance_server_980.py`).

**Root cause:** Sibling task #991 completed identical work before #981 was picked up. Task #981 was not cleaned up.

- Tier: T1 (duplicate cleanup)
- Follow-up tasks created: none
- Decision requests: none
- Recommendation: archive this task immediately
[[2026-04-19]]

## Architecture Review (2nd pass)

### Verdict: APPROVE (duplicate — all AC pre-satisfied)

Confirmed duplicate of archived #991. All 5 AC lines verified in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` lines 214–228:

| AC Line | Evidence | Status |
|---------|----------|--------|
| Pre-read via `_show_validated()` | L214: `pre_task = await _show_validated(app_ctx, task_id)` | ✅ |
| `collect_guidance("move", before, after)` | L227: call present | ✅ |
| Attach to `KanbanTask.guidance` | L227: `result.guidance = collect_guidance(...)` | ✅ |
| Status ordering from `board_config().statuses` | L226: `[s["name"] for s in app_ctx.engine.board_config().statuses]` | ✅ |
| Archived excluded from skip detection | Not in config statuses; `contextlib.suppress(Exception)` guards | ✅ |

### Rationale for APPROVE (not re-reject)

Previous cycle: rejected → research → confirmed duplicate → back to backlog. Re-rejecting creates infinite loop. All work is complete; advancing lets pipeline verify tests pass and archive.

### Downstream guidance

No implementation needed. Tests from #979 already pass. Builder/reviewer should confirm green suite and pass through.

Challenge: SKIPPED — premise already challenged in prior review cycle, research confirmed finding.
[[2026-04-19]]

## Test-Writer Notes

**Pass-through — all AC pre-satisfied by archived task #991.**

Verified existing test file: `serve/mcp-kanban/tests/test_guidance_move_task_973.py`
Class: `TestFromAC_MoveTaskGuidanceIntegration` (5 tests)

AC coverage check against `server.py` lines 214–228:

| AC Line | Evidence | Tested By |
|---------|----------|-----------|
| `move_task` pre-reads via `_show_validated()` | L214 | test_forward_skip_* |
| Invokes `collect_guidance("move", before, after)` | L227 | all 5 tests |
| Attaches result to `KanbanTask.guidance` | L227 | all 5 tests |
| Status ordering from `board_config().statuses` | L226 | all 5 tests |
| Archived excluded from skip detection | not in config statuses | test_archived_status |

All 5 tests confirm implementation is present and passing. No new failing tests applicable — implementation was completed by #991 before this task was picked up.

**No test file created.** Advancing to builder for suite confirmation and archive.
[[2026-04-19]]

## Builder Notes

- No code changes needed — all AC pre-satisfied by archived task #991.
- Pass-through confirmed per Test-Writer Notes.

### Evidence

- `serve/mcp-kanban/tests/test_guidance_move_task_973.py` — 5 TestFromAC tests present and passing.
- Full mcp-kanban suite: **72 passed**, 0 failed (0.71s).
- `ruff check serve/mcp-kanban/` — **clean** (exit 0).
- No files modified.
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: **72 passed, 0 failed** (exit 0)
- ruff: **clean** (exit 0)
- Coverage: `guidance.py` = 98%, `models.py` = 100%, `server.py` = 64% (pre-existing — builder made zero code changes)

### AC Compliance

| AC Line | Code Evidence | Test | Assertion Strength | Status |
|---------|---|---|---|---|
| `move_task` pre-reads via `_show_validated()` | server.py:215 `pre_task = await _show_validated(app_ctx, task_id)` | All 5 TestFromAC tests | STRONG | ✅ |
| Invoke `collect_guidance("move", before, after)` | server.py:219–221 | `test_forward_skip_guidance_references_from_and_to_status` | STRONG | ✅ |
| Attach to `KanbanTask.guidance` | server.py:220 `result.guidance = collect_guidance(...)` | All 5 TestFromAC tests assert on `result.guidance` | STRONG | ✅ |
| Status ordering from `board_config().statuses` | server.py:219 `[s["name"] for s in app_ctx.engine.board_config().statuses]` | `test_forward_skip_*` ordering tests | STRONG | ✅ |
| Archived excluded from skip detection | guidance.py:89–93 — `after.status` not in `status_names` raises ValueError, caught → returns `[]` | `test_archive_move_returns_empty_guidance` asserts `== []` | STRONG | ✅ |
| All #979 + existing tests pass | — | 72 passed full suite | N/A | ✅ |

### TestFromAC Integrity

Builder made zero code changes. No TestFromAC tests were modified or removed. All 5 tests in `TestFromAC_MoveTaskGuidanceIntegration` present and passing.

### Notes

- server.py at 64% coverage is pre-existing, not introduced by this task. AC-relevant paths (move_task guidance wiring) are covered by the TestFromAC suite.
- Archived exclusion works via implicit ValueError (archived not in board_config statuses list) — functionally correct and verified by exact equality assertion. Not a defect.

### Deductions

0 — no test failures, no lint violations, no AC gaps, no weak assertions.

### Verdict

**Confidence: .96 → PASS**
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Builder made zero code changes; all AC pre-satisfied by archived #991 |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns referenced |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | Research captured inline in task body; no separate research file |

### Files Updated

None — no docs impact.

### Scratch Files

No `.owlbear/scratch/981-*` files found; nothing to clean.

### Summary

Pure duplicate pass-through task. Review Evidence section present ✅. All 5 checklist items N/A with evidence. Gate passed.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `move_task` pre-reads via `_show_validated()` | server.py:215 `pre_task = await _show_validated(app_ctx, task_id)` | PASS |
| Invoke `collect_guidance("move", before, after)` | server.py:228 `result.guidance = collect_guidance(...)` | PASS |
| Attach to `KanbanTask.guidance` | server.py:228 same line | PASS |
| Status ordering from `board_config().statuses` | server.py:227 `[s["name"] for s in app_ctx.engine.board_config().statuses]` | PASS |
| Archived excluded from skip detection | guidance.py:88-94 ValueError catch returns `[]` | PASS |
| All #979 + existing tests pass | 5/5 TestFromAC in test_guidance_move_task_973.py | PASS |

### Test Results

- pytest: 664 passed, 27 failed (all failures outside task scope: 21 cockpit launch RED tests, 4 mcp-knowledge schema, 1 async, 1 missing SKILL.md). Zero mcp-kanban failures.
- ruff: clean

### Architect Quality: 4/5

AC was specific and verifiable. Task was a duplicate of archived #991 (task management overlap, not AC quality issue). Pipeline handled the duplicate correctly via reject/research/approve cycle.

### Deduction Breakdown

- AC lines without evidence: 0 (-.02 each, none applicable)
- Lint violations: 0
- AC quality score 4 (above 3 threshold): 0
- Missing reviewer evidence: 0 (present and detailed)
- Full-suite failures in task scope: 0

### Confidence: 1.00

### Action: archive
