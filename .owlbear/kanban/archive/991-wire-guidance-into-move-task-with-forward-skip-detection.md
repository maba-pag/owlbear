---
id: 991
title: Wire guidance into `move_task` with forward-skip detection
status: backlog
priority: needed
created: 2026-04-18T21:23:00.874612+00:00
updated: 2026-04-18T21:51:10.880751+00:00
tags:
- type:feature
- scope:mcp
- scope:kanban
parent: 973
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D2, D6.

## Problem
MCP `move_task` has no forward-skip detection. Currently delegates directly to engine without pre-reading the task.

## Acceptance Criteria
- `move_task` pre-reads the task via `_show_validated()` before calling `engine.move_task`.
- After engine call, calls `collect_guidance("move", before=pre_read_task, after=result_task, status_names=[s["name"] for s in board_config().statuses])`.
- Forward skip > 1 slot returns guidance with forward-skip message.
- Forward skip of exactly 1 slot → empty guidance.
- Backward moves → empty guidance.
- Moves to `archived` → empty guidance (excluded from skip detection).
- Integration test per case.

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/tests/test_guidance_move_task_973.py` (new)

## Dependencies
- Depends on: KanbanTask.guidance field task, guidance.py module task
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/move-task-guidance-991.md
- Sources: 7 studied, 6 high-relevance (all codebase-internal)
- Recommendation: Proceed with Brief Path A1, locked decisions D2/D6 — pre-read via `_show_validated()`, extract `status_names` from `board_config().statuses`, wire `collect_guidance("move", ...)` with try/except (confidence: .92)
- Key findings: (1) `move_task` is the only integration needing `before` state — uses existing `_show_validated()`. (2) `board_config().statuses` never includes archived, so skip detection auto-excludes archived moves. (3) TOCTOU between pre-read and engine call accepted per Brief R1.4. (4) Implementation is ~15 LOC, pattern identical to validated siblings #985/#989.
- Challenge: SKIPPED — approach locked via parent Brief 3-round architect debate
- Follow-up tasks created: none (task itself moves to backlog; deps #986/#987 exist)
- Decision requests: none — T1 autonomous, all decisions locked
- Dependencies: needs [986, 987] wired to `depends_on` before entering in-progress