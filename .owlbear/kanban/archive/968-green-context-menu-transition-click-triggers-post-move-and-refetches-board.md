---
id: 968
title: 'GREEN: Context menu transition-click triggers POST /move and refetches board'
status: archived
priority: important
created: 2026-04-18T16:07:43.830829+00:00
updated: 2026-04-18T19:53:40.041914+00:00
tags:
- cockpit
- frontend
- phase-2
- type:build
parent:
depends_on:
- 958
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Implement the click handler for context menu transition items so that clicking a transition sends POST /api/tasks/{id}/move, refetches the board on success, shows errors on failure, and closes the menu.

## Context

Task #958 writes RED tests covering the behavior. This task implements the minimal code to turn those tests green.

## Acceptance Criteria

- [ ] Clicking a transition item sends POST `/api/tasks/{id}/move` with `{status: target}`
- [ ] Board refetches after successful move (task appears in new column)
- [ ] Error message shown when move returns 422
- [ ] Error message shown when move fails with network error
- [ ] Context menu closes after clicking a transition item

## Files

- `serve/cockpit/web/src/KanbanBoard.tsx` (extend ContextMenuState with taskId, add onClick handler, add refetch to useBoard)
[[2026-04-18]]

## Architecture Review

### Verdict: PREMISE CHALLENGE — Already Implemented

All 5 AC items are already present in `serve/cockpit/web/src/KanbanBoard.tsx`:

| AC | Evidence | Line |
|---|---|---|
| AC1: POST /move with {status: target} | `handleTransitionClick` calls `fetch('/api/tasks/${taskId}/move', { method: 'POST', body: JSON.stringify({ status: targetStatus }) })` | ~237 |
| AC2: Board refetches after success | `refetchTasks()` called after ok check | ~246 |
| AC3: Error on 422 | `setMoveError('Move failed: ${res.status}')` for non-ok responses | ~241 |
| AC4: Error on network failure | `catch { setMoveError('Move failed: network error') }` | ~245 |
| AC5: Menu closes on click | `setContextMenu(null)` at start of handler | ~236 |

The `Files` section describes extending `ContextMenuState` with `taskId` and adding `onClick`/`refetch` — all already present. Implementation was completed in task #933 (P2-05: GREEN — Kanban board surface).

Tests from #958 (`TestFromAC_ContextMenuMove` in `KanbanBoard.test.tsx` L581-665) cover all 5 AC lines and should already pass.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: move wiring |
| Interface clarity | PASS | AC lines are specific |
| Dependency correctness | PASS | #958 archived (done) |
| Module layering | PASS | Frontend-only |
| TDD compliance | PASS | RED #958 done |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | **FAIL** | All 5 AC items already implemented in KanbanBoard.tsx via #933 |
| Pattern consistency | PASS | Follows existing fetch pattern |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | cockpit/frontend only |

### Challenge Results

- Challenger: **reconsider** (confidence 0.45)
- Key challenger findings: (C1) approving zero-delta task wastes pipeline; (C2) move-error tests verify element existence but not text content; (C3) refetchTasks() silently swallows failures
- Architect response: **accepted** — revised verdict from APPROVE to FAIL

### Recommendation

Archive this task as "completed by #933". No pipeline processing needed. Consider filing follow-ups for:

1. Test content assertions for move-error messages (C2 gap)
2. refetchTasks() silent failure handling (C3 gap)
[[2026-04-18]]

## Architecture Review (retry)

### Verdict: REJECT — Premise Fail (already implemented)

Independently verified all 5 ACs are present in `serve/cockpit/web/src/KanbanBoard.tsx` (L230-248) via #933. Zero-delta task — no pipeline processing needed.

Moved directly to `done` for archival.
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| POST /move with {status: target} | `handleTransitionClick` L298-301: `fetch('/api/tasks/${taskId}/move', { method: 'POST', body: JSON.stringify({ status: targetStatus }) })` | PASS |
| Board refetches after success | `refetchTasks()` at L306 | PASS |
| Error on 422 | `setMoveError('Move failed: ${res.status}')` at L303-304 | PASS |
| Error on network failure | `catch { setMoveError('Move failed: network error') }` at L308 | PASS |
| Menu closes on click | `setContextMenu(null)` at L294 | PASS |

### Test Results

- pytest: 604 passed, 6 failed (all in knowledge/mcp-knowledge domain, pre-existing, outside task scope)
- ruff: clean

### Architect Quality: 4/5

AC lines were specific and verifiable. Task was redundant (already completed by #933) — a decomposition/planning issue upstream, not an AC quality gap. Architect correctly caught this via premise challenge and short-circuited the pipeline.

### Deduction Breakdown

- Start: 1.00
- Test failures outside task scope: no deduction
- Lint clean: no deduction
- AC quality 4/5: no deduction
- Missing reviewer section: no deduction (expected for premise-fail zero-delta task)

### Confidence: 1.00

### Action: archive (zero-delta task, all AC satisfied by prior work in #933)
