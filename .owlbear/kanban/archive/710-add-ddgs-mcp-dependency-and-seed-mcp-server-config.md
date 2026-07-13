---
id: 710
title: Add ddgs[mcp] dependency and seed MCP server config
status: archived
priority: medium
created: 2026-04-09T02:40:39.8301993+02:00
updated: 2026-04-09T09:19:26.4803796+02:00
started: 2026-04-09T09:19:26.4803796+02:00
completed: 2026-04-09T09:19:26.4803796+02:00
tags:
    - scope:tools
    - ' type:build'
parent: 686
depends_on:
    - 707
class: standard
---

## Context
Parent: #686. TDD green phase for dependency and MCP config.

## Acceptance Criteria
- [ ] `ddgs[mcp]>=9.13,<10` added to [dependency-groups] dev in pyproject.toml
- [ ] seed/.vscode/mcp.json has ddgs entry: {"type":"stdio","command":"uv","args":["--project","{{owlbear_path}}","run","ddgs","mcp"]}
- [ ] setup/setup-guide.md documents ddgs MCP server (purpose, manual add steps for existing installs)
- [ ] `uv lock` succeeds with the new dependency
- [ ] Tests from task #707 pass (green)

## Files Affected
- pyproject.toml
- seed/.vscode/mcp.json (copilot-ignored — edit via terminal)
- setup/setup-guide.md
- uv.lock (regenerated)

## Constraints
- seed/.vscode/mcp.json is copilot-ignored; use terminal commands to edit

[[2026-04-09]] Thu 09:30
## Builder Notes
Archived: Redundant -- deliverables completed by parent #686 pipeline
