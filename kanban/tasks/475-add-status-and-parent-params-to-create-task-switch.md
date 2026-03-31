---
id: 475
title: Add status and parent params to create_task, switch to JSON output
status: backlog
priority: needed
created: 2026-03-31T06:06:12.5782763+02:00
updated: 2026-03-31T06:56:06.1464538+02:00
tags:
    - scope:mcp
    - ' type:build'
    - ' phase-2'
class: standard
---

## Acceptance Criteria\n\n- [ ] Add `status: str = ""` parameter to `create_task` tool; when non-empty, pass `--status`\n- [ ] Add `parent: int = 0` parameter; when > 0, pass `--parent`\n- [ ] Switch `create_task` output to `--json` (return created task as JSON object)\n- [ ] Tests cover: create with status override, create with parent, JSON return format\n- [ ] Update mcp-kanban SKILL.md to document new parameters

[[2026-03-31]] Tue 06:21
## Research

Doc: docs/research/create-task-status-parent-json.md

Key findings (.95 confidence):
- All 3 CLI flags (--status, --parent, --json) confirmed in kanban-md v0.33.0
- JSON output verified with actual create call
- Implementation is ~6 LOC following existing optional-param pattern
- show_task already uses --json (L141) as direct precedent
- parent uses int type with 0 sentinel

Follow-up task: #482 (ideation)

[[2026-03-31]] Tue 06:30
## Update: Add outputSchema\n\n- [ ] Define outputSchema for create_task return (task object)\n- [ ] Return structuredContent alongside text content
