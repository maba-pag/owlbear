---
id: 479
title: 'GREEN: implement modernized list_tasks (archived, limit, reverse, blocked tri-state, lean JSON)'
status: ideation
priority: needed
created: 2026-03-31T06:13:51.2541611+02:00
updated: 2026-03-31T06:13:51.2541611+02:00
tags:
    - scope:mcp
    - ' type:build'
    - ' phase-2'
depends_on:
    - 478
class: standard
---

## Acceptance Criteria

- [ ] Add archived: bool = False parameter; when True pass --archived
- [ ] Add limit: int = 0 parameter; when >0 pass --limit N
- [ ] Add reverse: bool = False parameter; when True pass --reverse
- [ ] Replace block_filter: str with blocked: bool | None = None; True=--blocked, False=--not-blocked, None=no flag
- [ ] Switch output from --compact to --json
- [ ] Parse JSON output, strip body/file/created/updated fields from each task, re-serialize
- [ ] All RED tests from #478 pass (GREEN phase)
- [ ] Update skills/mcp-kanban/SKILL.md parameter table for list_tasks

## Design Notes

Lean JSON: json.loads() on kanban-md output, list comprehension to strip fields, json.dumps() back. ~5 LOC change in list_tasks function.

Breaking change: block_filter -> blocked. Acceptable per project principles (no backwards compat).

See docs/research/modernize-list-tasks.md for full analysis.
