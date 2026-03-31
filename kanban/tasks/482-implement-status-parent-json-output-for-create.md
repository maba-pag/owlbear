---
id: 482
title: Implement status, parent, JSON output for create_task MCP tool
status: ideation
priority: needed
created: 2026-03-31T06:20:17.3046417+02:00
updated: 2026-03-31T06:20:17.3046417+02:00
tags:
    - scope:mcp
    - type:build
    - phase-2
depends_on:
    - 475
class: standard
---

## Acceptance Criteria

- [ ] Add status: str = '' parameter to create_task; when non-empty, pass --status
- [ ] Add parent: int = 0 parameter; when > 0, pass --parent {value}
- [ ] Append --json to create_task args unconditionally
- [ ] Unit tests: status flag, parent flag, parent=0 no flag, --json always present
- [ ] Integration tests: create+show roundtrip with status override, create+show with parent
- [ ] Update skills/mcp-kanban/SKILL.md create_task row to include status, parent params

## Implementation Notes

See docs/research/create-task-status-parent-json.md for full analysis.
Pattern: follow existing optional-param style (L148-176 in server.py).
show_task already uses --json (L141) -- same approach for create.
parent uses int type with 0 sentinel (CLI expects --parent int).
