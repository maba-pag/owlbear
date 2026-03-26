---
id: 17
title: Build mcp-project server
status: ideation
priority: important
created: 2026-03-26T17:21:36.1413972+01:00
updated: 2026-03-26T17:25:18.6270544+01:00
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
Build an MCP server that provides project metadata and context to agents.

## Acceptance Criteria
- [ ] MCP server in packages/mcp-project/ using Python MCP SDK
- [ ] Tool: project_info - return project name, type, path, owlbear installation path
- [ ] Tool: project_list - list all projects configured to use this owlbear installation
- [ ] Resource: project://readme - read-only project README
- [ ] Resource: project://structure - directory tree summary
- [ ] Server reads project config from .vscode/settings.json or project-level config
- [ ] Server communicates via stdio transport
- [ ] Register in .vscode/mcp.json and verify from VS Code
- [ ] SKILL.md with usage instructions for agents

## Context
Depends on R2 (MCP SDK) and F1 (monorepo skeleton). The project server helps agents understand what project they are working in and where owlbear assets live.
