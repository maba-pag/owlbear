---
id: 566
title: Update skill cheatsheets with MCP tool alternatives alongside CLI
status: archived
priority: needed
created: 2026-04-03T07:46:35.3687505+02:00
updated: 2026-04-03T12:39:05.6862797+02:00
started: 2026-04-03T12:39:05.6862797+02:00
completed: 2026-04-03T12:39:05.6862797+02:00
tags:
    - phase-2
    - ' scope:agent-config'
    - ' type:build'
parent: 483
depends_on:
    - 562
    - 563
class: standard
---

## Acceptance Criteria\n\n- [ ] All 9 skills with `## kanban-md Commands` cheatsheet tables updated: tdd-red, tdd-workflow, code-review, task-verification, docs-gate, research-workflow, arch-review, task-decomposition, curation-workflow\n- [ ] Each cheatsheet table adds MCP equivalent alongside CLI (e.g., `show {id}` row adds `show-task(task_id)` MCP column)\n- [ ] 2-3 skills with inline CLI references also updated: dispatch-planning, orchestration (and any others found)\n- [ ] MCP tool names and parameters match mcp-kanban SKILL.md (#563) reference\n- [ ] No existing CLI references removed — MCP is additive\n- [ ] Must pass #562 validation test\n\n## Scope\n\n~12 files: skills/{tdd-red,tdd-workflow,code-review,task-verification,docs-gate,research-workflow,arch-review,task-decomposition,dispatch-planning,orchestration,curation-workflow}/SKILL.md + any others with inline kanban CLI refs.\n\n## Notes\n\nResearch found 9 skills with cheatsheet tables + 2-3 with inline refs. The cheatsheet updates are mechanical: add an MCP column to existing tables. Inline refs need case-by-case MCP alternatives.
