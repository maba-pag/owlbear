---
id: 583
title: 'P2-B4: Rewrite instruction files to MCP-only'
status: archived
priority: medium
created: 2026-04-03 16:42:46.152360+02:00
updated: 2026-04-04 23:05:56.065725+02:00
started: 2026-04-04 23:03:31.431568+02:00
completed: 2026-04-04 23:05:56.065725+02:00
tags:
- scope:mcp
- ' phase-2'
- ' type:build'
parent: 484
depends_on:
- 484
class: standard
archival_reason: completed
archival_refs: []
---

**Source:** docs/research/phase-b-mcp-only-kanban-migration.md §3c\n\nStructural rewrites of agent-common.instructions.md and research-docs.instructions.md:\n\n1. Remove PS escaping section (pipe chars, arrow parsing, temp-file pattern — all MCP-obsolete)\n2. Rewrite Channel B section with MCP-only syntax (edit_task append_body)\n3. Rewrite Handoff/blocked section with end_work(outcome=block) + edit_task pattern\n4. Update Tool discipline section — remove kanban-md from terminal use list\n5. Update all remaining CLI refs to MCP equivalents\n6. research-docs.instructions.md L14 kanban-md create ref to create_task\n\n**AC:**\n- [ ] agent-common Channel B section uses edit_task/end_work MCP syntax only\n- [ ] PS escaping guidance removed (pipe, arrow, temp-file sections)\n- [ ] Tool discipline section no longer lists kanban-md as terminal tool\n- [ ] research-docs.instructions.md uses create_task MCP syntax\n- [ ] 0 kanban\\kanban-md.exe matches in instructions/ (grep verification)

[[2026-04-04]] Sat
Cancelled by orchestrator: zero remaining scope, target file absent. Parent #484 archived with all scope captured.

[[2026-04-04]] Sat 23:05
Cancelled: stale subtask, target file absent, scope captured by archived parent #484.
