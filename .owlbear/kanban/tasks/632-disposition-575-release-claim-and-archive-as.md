---
id: 632
title: 'Disposition #575: release claim and archive as resolved-by-architecture'
status: ideation
priority: nice-to-have
created: 2026-04-05T12:57:54.0576608+02:00
updated: 2026-04-05T12:57:54.0576608+02:00
tags:
    - phase-2
    - ' scope:kanban'
    - ' type:chore'
class: standard
---

## Acceptance Criteria

- [ ] #575 claim released (currently claimed at ideation)
- [ ] #575 archived as resolved-by-architecture (superseded by #486 DRY consolidation, same root cause as #576)
- [ ] Parent #483 completion criteria re-evaluated: if all 6 subtasks now archived, note in body that parent is fully resolved

## Context

#575 research (.78 confidence) recommends closing as resolved-by-architecture. The v2 workspace correctly factors MCP lifecycle: generic pattern in h-mcp-kanban (single source), agent-specific outcomes inline in kanban protocol blocks. Original AC premise (CLI-to-MCP annotation) no longer applies — same supersession chain as #576 (#484 removed CLI, #486 consolidated to DRY).

#575 is still claimed at ideation with no disposition action taken. The separate follow-up #625 (restore #574 callouts) is independent and already at todo.

## Files

.owlbear/kanban/tasks/575-*.md, .owlbear/kanban/tasks/483-*.md
