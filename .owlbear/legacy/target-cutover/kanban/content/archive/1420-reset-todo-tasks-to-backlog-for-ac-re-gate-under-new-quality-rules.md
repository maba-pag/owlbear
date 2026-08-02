---
id: 1420
title: Reset todo tasks to backlog for AC re-gate under new quality rules
status: archived
priority: medium
created: 2026-05-07T23:54:22.341303+00:00
updated: 2026-05-08T13:19:20.215592+00:00
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
[[2026-05-08]]
## Builder Notes
- Scope executed: board-state reset only (no code/file changes).
- Pre-check (`list_tasks status=todo`) confirmed target IDs in `todo`: #1413, #1428, #1430, #1431, #1432.
- Attempted operation: `edit_task(task_id=1413, status=backlog)` as fallback for missing `move_task` tool.
- Tool failure: `string indices must be integers, not 'str'` from kanban MCP `edit_task` when setting status.
- Result: Unable to perform required todo→backlog transitions from builder tool surface.
- Requested fallback per task body: orchestrator executes reset for IDs #1413, #1428, #1430, #1431, #1432.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | orchestrator | Execute board reset by moving #1413, #1428, #1430, #1431, #1432 from `todo` to `backlog` using a working kanban operation path (`move_task` or equivalent) | .owlbear/kanban/tasks/*.md | Task AC P1 + MCP failure on `edit_task(status=backlog)`: `string indices must be integers, not 'str'` |
| 2 | builder | Re-run P3 verification after orchestrator move: confirm target IDs absent from `todo` and present in `backlog`; ensure #1417 and #1427 unchanged | .owlbear/kanban/tasks/*.md | AC P2/P3 verification requirement |

[[2026-05-08]]
## Builder Notes
- Scope: board-state reset only (no repo file/code changes).
- Pre-check (`list_tasks status=todo`) confirms target IDs still in `todo`: #1413, #1428, #1430, #1431, #1432.
- Additional live state observed: #1417 remains in `todo`; #1427 is currently in `backlog` (board changed since prior note).
- Attempted required mutation path: `edit_task(task_id=1413, status=backlog)`.
- Tool result: `string indices must be integers, not 'str'` (kanban MCP status update path failure).
- Required `move_task` operation is not available in this builder MCP tool surface, and fallback status edit is failing.
- Outcome: unable to execute AC P1/P2 transition from this agent tool surface.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | orchestrator | Execute todo→backlog transitions for #1413, #1428, #1430, #1431, #1432 using a working kanban operation path that supports status moves (`move_task` or equivalent) | .owlbear/kanban/tasks/*.md | AC P1 + live `edit_task(..., status=backlog)` failure: `string indices must be integers, not 'str'` |
| 2 | builder | Re-run AC P3 verification after successful transitions: confirm listed IDs absent from `todo` and present in `backlog`, with unaffected statuses for non-target tasks | .owlbear/kanban/tasks/*.md | AC P2/P3 verification gate |

[[2026-05-08]]
## Builder Notes
- Non-implementation task — no code/file changes needed.
- Verified AC state from live board:
  - `todo` currently contains only #1417 and #1422 (targets #1413, #1428, #1430, #1431, #1432 are no longer in todo).
  - Direct task checks confirm #1413, #1428, #1430, #1431, and #1432 are all in `backlog`.
  - Non-target state remained untouched for active todo set (#1417 and #1422).
- P1/P2/P3 satisfied by current board state; passing to review.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner skipped: td:0 board-operation task with no executable source or task-local test surface.
- Lint/Coverage: N/A for this review.

### Live Board Evidence
- Review-time `list_tasks status=todo` returned `#1417`, `#1427`, `#1430`, `#1431`, `#1432`.
- Review-time `list_tasks status=backlog` returned `#1413` and `#1428` among active backlog tasks.
- Task #1420 identifies the reset target set as `#1413`, `#1428`, `#1430`, `#1431`, `#1432` at `.owlbear/kanban/tasks/1420-reset-todo-tasks-to-backlog-for-ac-re-gate-under-new-quality-rules.md:49-53`.
- The research artifact excludes `#1417` and `#1427` from the reset because they entered `todo` after A2 deploy at `.owlbear/research/1420-todo-reset-for-ac-regate.md:58-59`.

### Timeline Reconstruction
- Builder first proved the five targets were still in `todo` and that its own fallback mutation path failed: `.owlbear/kanban/tasks/1420-reset-todo-tasks-to-backlog-for-ac-re-gate-under-new-quality-rules.md:103-106`.
- Builder later recorded that the five targets were no longer in `todo` and were in `backlog`: `.owlbear/kanban/tasks/1420-reset-todo-tasks-to-backlog-for-ac-re-gate-under-new-quality-rules.md:136`.
- Three of those targets are now back in `todo`, but each carries a later Architecture Review advancement back to `todo`:
  - `.owlbear/kanban/tasks/1430-p1-02-directive-rewrites-in-w-ideation-mediation-skill-md.md:77-79`
  - `.owlbear/kanban/tasks/1431-p1-03-directive-rewrite-tier-presentation-in-w-ideation-discovery-skill-md.md:85-87`
  - `.owlbear/kanban/tasks/1432-p1-04-agent-enforcement-lines-verification-criteria-updates.md:105-107`
- Review-time `show_task` reported `#1430` updated `2026-05-08T12:18:50.747537+00:00`, `#1431` updated `2026-05-08T12:19:13.999663+00:00`, and `#1432` updated `2026-05-08T12:22:21.442059+00:00`, all later than #1420's pre-claim updated timestamp `2026-05-08T12:10:10.724595+00:00`. That timing is consistent with reset-to-`backlog` followed by architect re-gate back to `todo`, not with the reset failing.
- Non-target tasks remained untouched in `todo`: `.owlbear/kanban/tasks/1417-add-sarif-upload-to-github-code-scanning-in-megalinter-workflow.md:4` and `.owlbear/kanban/tasks/1427-implement-planner-skill-updates-h-ac-quality-wiring-consolidation-test-logic-rou.md:5`.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| P1: tasks in `todo` at A2 deploy moved to `backlog` | Target set documented at `1420:49-53`; live board now shows `#1413` and `#1428` in `backlog` (`1413:4`, `1428:4`) and `#1430/#1431/#1432` have subsequent architect re-gate artifacts proving they progressed through the intended reset path | PASS |
| P2: reset affects only that `todo` set; other statuses untouched | Excluded tasks `#1417` and `#1427` remain in `todo` (`1417:4`, `1427:5`); no evidence of unrelated task movement caused by #1420 | PASS |
| P2: backlog tasks become subject to architect re-gate | `#1430/#1431/#1432` each have Architecture Review sections advancing them to `todo` at `1430:77-79`, `1431:85-87`, `1432:105-107` | PASS |
| P3: verify no pre-existing tasks remain and confirm arrival | Builder recorded the intermediate verification at `1420:136`; current board no longer shows that exact intermediate state because three tasks have already been re-gated forward, but the combined board + task-history artifacts independently prove the reset effect | PASS |

### Deductions
- 0.04: raw `list_tasks` output for the intermediate P3 checkpoint was not preserved in the task body.
- 0.02: builder final note says `#1422` instead of `#1427`, so the prose summary itself is slightly sloppy even though the board artifacts support the intended conclusion.

### Verdict
- PASS. The reset occurred, the excluded `todo` tasks stayed untouched, and the three apparently-missing backlog tasks have already completed the next architect re-gate step.
- Confidence: 0.93

### Action
- Advancing to `docs`.
[[2026-05-08]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Board-state operation only; no prose docs reference task status moves |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1420-todo-reset-for-ac-regate.md` exists and is linked from task body |
| 5 | Diagram maintenance (describes match) | Yes | N/A | `kanban.excalidraw` describes `.owlbear/kanban/**` — matches board task files, but changes were pure task-status moves (board data), not structural kanban system changes; diagram content unaffected |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/kanban/tasks/1413*.md` etc. | OUT (board data) | N/A |
| `.owlbear/research/1420-todo-reset-for-ac-regate.md` | IN | Verified present and linked |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1420-*` scratch files found)
[[2026-05-08]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| P1: All tasks in todo at A2 deploy moved to backlog | #1413 status=backlog, #1428 status=backlog, #1430/#1431/#1432 have Architecture Review sections proving re-gate from backlog (now in review) | PASS |
| P2: Only target set affected; other statuses untouched | #1417 remains in todo (excluded per research doc); #1427 in review (excluded, progressed normally) | PASS |
| P2: Backlog tasks subject to architect re-gate | #1430, #1431, #1432 each received new Architecture Review with APPROVE verdict after reset | PASS |
| P3: Verification via list_tasks confirming state | Builder recorded intermediate verification; current board state independently confirms all 5 targets passed through backlog | PASS |

### Test Results
- pytest: 2945 passed, 195 failed (pre-existing failures in engine accessor migration, memory model, cockpit view, decisions, edit task contracts; NONE related to #1420 board-state change)
- ruff: 12 violations (all in serve/knowledge, serve/tools; pre-existing, unrelated to this task)
- No code changes in this task; failures are background debt

### Architect Quality: 4/5
Specific AC with exact task IDs, tools, and verification commands. Clear in/out scope. Minor issue: P2 used twice with different semantics (state assertion vs policy statement). Overall well-specified for a board-operation task.

### Deduction Breakdown
- Start: 1.00
- P3 verification evidence is indirect (builder assertion + current board state, raw list_tasks output not preserved): -.02
- Builder documentation inconsistency (#1422 vs #1427 in final note, cosmetic): -.01

### Confidence: .97
### Action: archive

### Commit Verification
- Research doc: f73350be (docs: research todo reset for AC re-gate)
- No source code commits required (board-state-only task)