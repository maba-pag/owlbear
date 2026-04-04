---
id: 580
title: 'P2-B1: Remove CLI refs from agent files, MCP-only'
status: ideation
priority: needed
created: 2026-04-03T16:42:18.9233775+02:00
updated: 2026-04-03T16:42:18.9233775+02:00
tags:
    - scope:agents
    - ' scope:mcp'
    - ' phase-2'
    - ' type:build'
parent: 484
depends_on:
    - 484
class: standard
---

**Source:** docs/research/phase-b-mcp-only-kanban-migration.md §3a\n\nReplace all 44 kanban\\kanban-md.exe references across 11 agent files with MCP tool calls. Each agent already has MCP tool blockquotes from Phase A (#483) — remove the CLI commands and make MCP the only syntax shown.\n\n**Files:** architect, auditor, builder, curator, kanban-planner, planner, researcher, reviewer, scribe, test-writer, writer (.agent.md)\n\n**AC:**\n- [ ] 0 kanban\\kanban-md.exe matches in agents/ (grep verification)\n- [ ] All output_format sections use MCP tool syntax only\n- [ ] Example sections use MCP tool calls (start_work, edit_task, end_work)\n- [ ] kanban-planner examples use create_task instead of kanban-md create\n- [ ] Existing MCP blockquotes remain (from Phase A)
