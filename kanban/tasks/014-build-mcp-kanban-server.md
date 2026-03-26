---
id: 14
title: Build mcp-kanban server
status: ideation
priority: needed
created: 2026-03-26T17:20:58.5923925+01:00
updated: 2026-03-26T17:25:18.027057+01:00
tags:
    - phase-1
    - scope:mcp
    - type:build
depends_on:
    - 2
    - 7
class: standard
---

## Objective
Build an MCP server that wraps kanban-md.exe, exposing board operations as MCP tools. This abstracts the kanban implementation so it can be swapped later.

## Acceptance Criteria
- [ ] MCP server in packages/mcp-kanban/ using Python MCP SDK
- [ ] Tool: kanban_list - list tasks with optional filters (status, tag, priority)
- [ ] Tool: kanban_show - show a single task by ID
- [ ] Tool: kanban_create - create a new task
- [ ] Tool: kanban_edit - edit task fields (status, priority, tags, body, claim)
- [ ] Tool: kanban_move - move task to a new status
- [ ] Resource: board://summary - read-only board snapshot
- [ ] Server communicates via stdio transport
- [ ] Server discovers kanban-md.exe path from config or environment
- [ ] Error handling: clear messages when kanban-md.exe is missing or fails
- [ ] Register in .vscode/mcp.json and verify tool calls from VS Code
- [ ] SKILL.md with usage instructions for agents

## Context
Depends on R2 (MCP SDK) and F1 (monorepo skeleton). The kanban MCP server is the abstraction layer over kanban-md. When we eventually replace kanban-md, only this server changes.
