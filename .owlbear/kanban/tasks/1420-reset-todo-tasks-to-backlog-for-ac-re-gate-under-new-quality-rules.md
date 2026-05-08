---
id: 1420
title: Reset todo tasks to backlog for AC re-gate under new quality rules
status: in-progress
priority: needed
created: 2026-05-07T23:54:22.341303+00:00
updated: 2026-05-08T08:57:46.734734+00:00
tags:
- pipeline
- ws-ac-quality
- scope:board
- type:config
parent: 1403
depends_on:
- 1405
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: All tasks that were in `todo` at the time A2 (#1405) deployed are moved to `backlog` via `move_task`
P2: Before state: N tasks in `todo`. After state: those N tasks are in `backlog`; tasks that were in `in-progress`, `review`, or `done` are untouched
P2: Tasks in `backlog` are now subject to architect re-gate under new AC quality rules (h-ac-quality)
P3: Verification by `list_tasks status=todo` confirming no pre-existing tasks remain; `list_tasks status=backlog` confirming they arrived

## Fallback

If the assigned agent cannot perform board operations (no MCP kanban tools available), return a Channel B message requesting the orchestrator to execute the reset. Include the list of task IDs to move.

## Scope

**In scope:** Board state changes only — move tasks from `todo` to `backlog`
**Out of scope:** Modifying task content, re-writing AC, any skill/code changes

[[2026-05-08]]
## Research
- Research doc: .owlbear/research/1420-todo-reset-for-ac-regate.md
- Sources: 4 studied, 4 high-relevance (git tree snapshots + live board state)
- Recommendation: Move 5 tasks from todo→backlog (confidence: 0.92)

### Findings
Git snapshot at A2 builder commit (9a9e5e10, 2026-05-08 03:20) shows 7 tasks in todo. 2 have since moved to review (untouched per AC P2). 5 remain in todo and should be moved to backlog:
- #1413 (D2: CI/SAST baseline) — has arch review but pre-deployment
- #1428 (Ideation UX parent) — planner bypassed backlog
- #1430 (P1-02: Directive rewrites)
- #1431 (P1-03: Directive rewrite)
- #1432 (P1-04: Agent enforcement)

2 tasks currently in todo (#1417, #1427) were NOT in todo at deploy time — they entered todo after A2 deployed and have proper architect APPROVEs. Leave untouched.

Challenge: skipped — no competing options, straightforward board operation.
Commit: f73350be
[[2026-05-08]]


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Board state changes only — move tasks todo→backlog |
| Interface clarity | PASS | AC specifies exact task IDs, tool (`move_task`), direction, verification |
| Dependency correctness | PASS | #1405 deployed per git commit 9a9e5e10; archived |
| Module layering | N/A | No code changes |
| TDD compliance | N/A | No testable Python code |
| KISS/YAGNI | PASS | Minimal mechanical operation |
| Premise challenge | PASS | New AC quality rules require re-gate of pre-deployment approvals |
| Pattern consistency | PASS | Standard MCP kanban tool usage |
| Security surface | PASS | No system boundaries affected |
| Single domain | PASS | Kanban/pipeline domain only |

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- AC P1: (td:0) — mechanical MCP move_task calls
- AC P2: (td:0) — state assertion via list_tasks output, not pytest
- AC P2 (second): (td:0) — policy statement, not testable
- AC P3: (td:0) — verification via list_tasks CLI output
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Added `type:config` tag for test-writer pass-through. Approved to todo. Builder executes 5× move_task(id, backlog) for #1413, #1428, #1430, #1431, #1432, then verifies via list_tasks.

[[2026-05-08]]
Architecture review complete. All criteria PASS. Pure board-operation task (td:0 across all AC). Added type:config for test-writer pass-through. Builder targets: move_task for #1413, #1428, #1430, #1431, #1432 from todo→backlog, verify via list_tasks.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- All AC lines annotated (td:0): mechanical MCP board-state moves + list_tasks verification, not pytest-testable.
- Architect explicitly marked Test-writer: SKIP.
- Passing through to builder.