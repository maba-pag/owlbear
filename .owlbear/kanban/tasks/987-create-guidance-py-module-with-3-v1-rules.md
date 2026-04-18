---
id: 987
title: Create `guidance.py` module with 3 V1 rules
status: backlog
priority: needed
created: 2026-04-18T21:22:36.980680+00:00
updated: 2026-04-18T21:45:50.027195+00:00
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
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D2, D5.

## Problem
No guidance computation logic exists. Need a flat rule registry with `collect_guidance()` function.

## Acceptance Criteria
- New module: `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py`.
- `collect_guidance(operation: str, before: KanbanTask | None, after: KanbanTask, **kwargs) -> list[str]` function.
- Three V1 rules:
  1. **Block DR rule:** when `after.blocked is True`, emit "⚠️ ACTION REQUIRED: Create a Decision Request for this block via the scribe agent (see w-decision-routing). Blocks without a DR are invisible to the pipeline."
  2. **Forward-skip rule:** when `operation == "move"` and status jumps > 1 slot forward (excluding archived), emit guidance about unusual forward skip.
  3. **Success/commit rule:** when `operation == "end_work"` and outcome is "success", emit "Reminder: verify your changes are committed and pushed before this task advances."
- Flat `(predicate, message_template)` list — no classes, no decorators.
- Adding a fourth rule = appending one tuple.
- Unit test per rule: positive case (guidance emitted) and negative case (no guidance).
- Block rule skips when `block:user` tag is present on the `after` task.
- Forward-skip rule uses `status_names: list[str]` from kwargs (passed by caller from `board_config().statuses`).

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` (new)
- `serve/mcp-kanban/tests/test_guidance_rules_973.py` (new)
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/guidance-module-987.md
- Sources: 6 studied, 4 high-relevance (all codebase-internal)
- Recommendation: Pattern B — mixed static/callable message tuples in flat registry (confidence: .90)
- Key findings: (1) `collect_guidance()` returns `list[str]`, caller assigns to `task.guidance` — no dependency on #986. (2) Forward-skip uses `status_names` kwarg with index arithmetic; `board_config().statuses` never includes archived. (3) Block DR rule checks `after.blocked is True` and `"block:user" not in after.tags`. (4) Tests use constructed `KanbanTask` instances — 2 tests per rule (positive + negative) + edge cases.
- Follow-up tasks created: none (task itself moves to backlog)
- Decision requests: none — all decisions locked by parent Brief D2, D5, D6