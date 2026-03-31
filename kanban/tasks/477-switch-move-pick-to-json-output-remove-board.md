---
id: 477
title: Switch move/pick to JSON output, remove board_context tool
status: backlog
priority: needed
created: 2026-03-31T06:06:24.5978486+02:00
updated: 2026-03-31T06:47:37.9199746+02:00
tags:
    - scope:mcp
    - ' type:build'
    - ' phase-2'
class: standard
---

## Acceptance Criteria\n\n- [ ] Switch `move_task` output to `--json` (return moved task as JSON object)\n- [ ] Switch `pick_task` output to `--json` (return picked task as JSON object)\n- [ ] Remove `board_context` tool entirely from server.py (YAGNI)\n- [ ] Tests cover: move returns JSON, pick returns JSON, board_context no longer registered\n- [ ] Update mcp-kanban SKILL.md: remove board_context, update move/pick docs\n\n## Design Notes\n\n- board_context is unused; removal simplifies the tool surface\n- move_task and pick_task are read-last, so JSON return gives structured confirmation

[[2026-03-31]] Tue 06:22
## Research
Research complete. See docs/research/move-pick-json-remove-board-context.md

Key findings (.95 confidence):
- kanban-md move and pick both support --json (global flag, v0.33.0)
- board_context has zero consumers outside mcp-kanban package itself
- Implementation is 4 LOC changed in server.py (2 additions, 8 removals)
- Pattern: identical to existing show_task --json usage

Follow-up tasks created at ideation:
- #485 TDD RED tests (add --json assertions, remove board_context tests)
- #489 GREEN build (add --json to move/pick, remove board_context)
- #490 Docs update (update mcp-kanban SKILL.md)

[[2026-03-31]] Tue 06:30
## Update: Add outputSchema + tool annotations\n\n- [ ] Define outputSchema for move_task and pick_task return (task object)\n- [ ] Return structuredContent alongside text content\n- [ ] Add tool annotations to ALL tools in server.py:\n  - list_tasks: readOnlyHint=true, idempotentHint=true\n  - show_task: readOnlyHint=true, idempotentHint=true\n  - create_task: (no special hints)\n  - move_task: (no special hints)\n  - edit_task: (no special hints)\n  - pick_task: (no special hints)\n  - start_work: (no special hints)\n  - end_work: (no special hints)
