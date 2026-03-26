---
id: 25
title: Multi-project setup test
status: ideation
priority: important
created: 2026-03-26T17:23:32.2827073+01:00
updated: 2026-03-26T17:25:19.8416388+01:00
tags:
    - phase-2
    - scope:build
    - type:test
depends_on:
    - 12
    - 18
class: standard
---

## Objective
Validate the multi-project model: create a test project, run setup, verify agents/skills/MCP servers work correctly from the project context.

## Acceptance Criteria
- [ ] Create a test project directory (e.g., test-project/)
- [ ] Run owlbear setup from the test project
- [ ] Verify .vscode/settings.json points to owlbear agents and skills
- [ ] Verify .vscode/mcp.json references owlbear MCP servers
- [ ] Open test project in VS Code and verify agents appear in agent picker
- [ ] Verify skills auto-load when relevant topics are discussed
- [ ] Verify MCP tools are callable from Copilot Chat
- [ ] Verify project-level copilot-instructions.md overrides work
- [ ] Test adding a project-specific agent override in .github/agents/
- [ ] Document the complete setup-to-working experience

## Context
Depends on F6 (setup script) and M5 (MCP server registry). This validates the 'clone = install' distribution model end-to-end.
