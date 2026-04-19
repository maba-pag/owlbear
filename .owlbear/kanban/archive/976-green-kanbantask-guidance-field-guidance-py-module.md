---
id: 976
title: 'GREEN: KanbanTask.guidance field + guidance.py module'
status: backlog
priority: needed
created: 2026-04-18T21:18:03.809586+00:00
updated: 2026-04-18T21:18:03.809586+00:00
tags:
- scope:mcp
- scope:kanban
- type:build
parent: 973
depends_on:
- 974
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. GREEN phase per w-tdd-green. Makes #974 tests pass.

## Acceptance Criteria
Files:
- `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`
- new `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py`

Per Brief decisions D4 + D5:
- Add `guidance: list[str] = []` as the FIRST declared field on `KanbanTask` (Pydantic v2 declaration-order JSON serialization places it first).
- Create `guidance.py` with flat rule list. Each rule is a `(predicate, message_template)` tuple.
- One function: `collect_guidance(operation: str, before: KanbanTask | None, after: KanbanTask, **kwargs) -> list[str]`.
- V1 ships three rules:
  1. `operation in ("edit_block", "end_work_block")` and `block:user` tag NOT in `after.tags` → DR-required message
  2. `operation == "move"` and `after.status` is > 1 slot ahead of `before.status` (in the engine's status order) → forward-skip message
  3. `operation == "end_work_success"` → commit-pushed message
- No classes, no decorators.

All tests in #974 pass; all existing kanban MCP tests still pass.