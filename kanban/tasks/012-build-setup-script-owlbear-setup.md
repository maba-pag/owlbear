---
id: 12
title: Build setup script (owlbear setup)
status: ideation
priority: needed
created: 2026-03-26T17:20:25.3978372+01:00
updated: 2026-03-26T17:20:25.3978372+01:00
tags:
    - phase-1
    - scope:cli
    - type:build
depends_on:
    - 7
class: standard
---

## Objective
Build the setup script that initializes a project to use owlbear. Run from any project directory, it creates the .vscode/ configuration pointing back to the owlbear installation.

## Acceptance Criteria
- [ ] scripts/setup.py can be run as: python ../owlbear/scripts/setup.py
- [ ] Creates .vscode/settings.json with chat.agentFilesLocations pointing to owlbear/agents/
- [ ] Creates .vscode/settings.json with chat.agentSkillsLocations pointing to owlbear/skills/
- [ ] Creates .vscode/mcp.json with MCP server configuration (kanban, knowledge, project)
- [ ] Creates kanban/ directory with config.yml and tasks/
- [ ] Creates data/knowledge/ directory for project KB
- [ ] Creates .github/copilot-instructions.md template with project name placeholder
- [ ] Detects relative path to owlbear installation automatically
- [ ] Idempotent: running twice does not overwrite existing config
- [ ] Prints clear success message with next steps

## Context
Depends on F1 (monorepo skeleton) for knowing the exact paths. This is the 'clone = install' entry point. Setup takes 30 seconds and a project is ready to use owlbear.
