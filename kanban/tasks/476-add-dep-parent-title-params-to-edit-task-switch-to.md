---
id: 476
title: Add dep/parent/title params to edit_task, switch to JSON output
status: backlog
priority: needed
created: 2026-03-31T06:06:19.0737281+02:00
updated: 2026-03-31T06:42:41.5372434+02:00
tags:
    - scope:mcp
    - ' type:build'
    - ' phase-2'
class: standard
---

## Acceptance Criteria\n\n- [ ] Add `add_dep: int = 0` parameter; when > 0, pass `--add-dep`\n- [ ] Add `remove_dep: int = 0` parameter; when > 0, pass `--remove-dep`\n- [ ] Add `parent: int = 0` parameter; when > 0, pass `--parent`\n- [ ] Add `title: str = ""` parameter; when non-empty, pass `--title` (rename capability)\n- [ ] Switch `edit_task` output to `--json` (return edited task as JSON object)\n- [ ] Tests cover: add/remove dep, set parent, rename title, JSON return format\n- [ ] Update mcp-kanban SKILL.md to document new parameters\n\n## Design Notes\n\n- add_dep/remove_dep are single int per call (call multiple times for multiple deps)\n- Existing `tags` param stays as replace-all; no add_tag/remove_tag added (accepted trade-off)

[[2026-03-31]] Tue 06:20
## Research
See docs/research/edit-task-dep-parent-title-json.md for full analysis.

Key findings (.90 confidence):
- All 4 CLI flags verified in kanban-md v0.33.0
- show_task already uses --json, same pattern applies
- Mechanical implementation, no design decisions needed
- 4 new params + unconditional --json + 6 new tests
- No follow-up tasks beyond #476 itself

[[2026-03-31]] Tue 06:21
## Research
See docs/research/edit-task-dep-parent-title-json.md for full analysis.

Key findings (.90 confidence):
- All 4 CLI flags verified in kanban-md v0.33.0
- show_task already uses --json, same pattern applies
- Mechanical implementation, no design decisions needed
- 4 new params + unconditional --json + 6 new tests
- No follow-up tasks beyond #476 itself

[[2026-03-31]] Tue 06:21
## Research
See docs/research/edit-task-dep-parent-title-json.md for full analysis.

Key findings (.90 confidence):
- All 4 CLI flags verified in kanban-md v0.33.0
- show_task already uses --json, same pattern applies
- Mechanical implementation, no design decisions needed
- 4 new params + unconditional --json + 6 new tests
- No follow-up tasks beyond #476 itself

[[2026-03-31]] Tue 06:21
## Research - see docs/research/edit-task-dep-parent-title-json.md

Research complete

[[2026-03-31]] Tue 06:30
## Update: Add outputSchema\n\n- [ ] Define outputSchema for edit_task return (task object)\n- [ ] Return structuredContent alongside text content
