---
id: 582
title: 'P2-B3: Update inline-ref skills to MCP-only'
status: ideation
priority: needed
created: 2026-04-03T16:42:36.5956013+02:00
updated: 2026-04-03T16:42:36.5956013+02:00
tags:
    - scope:skills
    - ' scope:mcp'
    - ' phase-2'
    - ' type:build'
parent: 484
depends_on:
    - 484
class: standard
---

**Source:** docs/research/phase-b-mcp-only-kanban-migration.md §3a\n\nUpdate 5 skill files that have inline (non-cheatsheet) CLI references: dispatch-planning, decision-requests, kanban-md, orchestration, research-workflow.\n\nThe kanban-md SKILL.md requires special handling: its claiming protocol examples should use MCP syntax. The skill's purpose shifts from CLI reference to MCP claiming protocol reference (the mcp-kanban skill already covers tool parameters).\n\n**AC:**\n- [ ] dispatch-planning, decision-requests, orchestration, research-workflow use MCP calls\n- [ ] kanban-md SKILL.md claiming protocol uses MCP tool syntax\n- [ ] kanban-md SKILL.md cross-references mcp-kanban for full tool parameters\n- [ ] 0 kanban\\kanban-md.exe matches in these 5 files (grep verification)
