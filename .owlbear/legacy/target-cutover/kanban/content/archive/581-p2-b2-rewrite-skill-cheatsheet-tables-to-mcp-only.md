---
id: 581
title: 'P2-B2: Rewrite skill cheatsheet tables to MCP-only'
status: archived
priority: medium
created: 2026-04-03 16:42:28.384900+02:00
updated: 2026-04-04 23:05:43.574137+02:00
started: 2026-04-04 23:03:31.415228+02:00
completed: 2026-04-04 23:05:43.574137+02:00
tags:
- scope:skills
- ' scope:mcp'
- ' phase-2'
- ' type:build'
parent: 484
depends_on:
- 484
class: standard
archival_reason: completed
archival_refs: []
---

**Source:** docs/research/phase-b-mcp-only-kanban-migration.md §3a, §3c\n\nRewrite kanban-md cheatsheet tables in 8 skill SKILL.md files to use MCP-only syntax. Tables currently have CLI commands with MCP rows at the bottom — invert to MCP-first, remove CLI rows.\n\n**Files:** arch-review, code-review, curation-workflow, docs-gate, task-decomposition, task-verification, tdd-red, tdd-workflow (SKILL.md)\n\n**AC:**\n- [ ] All 8 cheatsheet-style skills have MCP tool commands as primary syntax\n- [ ] Cheatsheet table headers updated (e.g., MCP Commands not kanban-md Commands)\n- [ ] Inline CLI commands in procedural steps replaced with MCP equivalents\n- [ ] arch-review delete operation noted as terminal-only exception\n- [ ] 0 kanban\\kanban-md.exe matches in these 8 files (grep verification)

[[2026-04-04]] Sat
Cancelled by orchestrator: zero remaining scope, stale pre-reorganization research. Parent #484 archived with all scope captured.

[[2026-04-04]] Sat 23:05
Cancelled: stale subtask, scope covered by archived parent #484.
