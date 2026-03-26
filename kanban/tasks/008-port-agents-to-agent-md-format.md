---
id: 8
title: Port agents to .agent.md format
status: ideation
priority: needed
created: 2026-03-26T17:19:41.2513734+01:00
updated: 2026-03-26T17:56:02.5159936+01:00
tags:
    - phase-1
    - scope:agents
    - type:build
depends_on:
    - 4
class: standard
---

## Objective
Port all 9 v1 agents from .github/agents/ to the v2 agents/ directory, replacing PydanticAI tool references with VS Code built-in tools and MCP server tools.

## Acceptance Criteria
- [ ] Port architect.agent.md - replace tool references
- [ ] Port builder.agent.md - replace tool references
- [ ] Port reviewer.agent.md - replace tool references
- [ ] Port researcher.agent.md - replace tool references
- [ ] Port planner.agent.md - replace tool references
- [ ] Port writer.agent.md - replace tool references
- [ ] Port auditor.agent.md - replace tool references
- [ ] Port curator.agent.md - replace tool references
- [ ] Port orchestrator.agent.md - replace tool references
- [ ] Each agent's tools: field maps to correct VS Code/MCP tool names
- [ ] Each agent's agents: field enables correct subagent handoffs
- [ ] Test at least 2 agents in VS Code Copilot Chat

## Context
Depends on R4 (.agent.md format validation) for the tool name mapping. V1 agents are already in .agent.md format but reference PydanticAI toolsets that won't exist in v2.

[[2026-03-26]] Thu 17:56
## Additional AC
- [ ] Write v2 agents to agents/ at repo root (not .github/agents/)
- [ ] Update .vscode/settings.json chat.agentFilesLocations to include agents/
- [ ] After v2 agents verified working, delete .github/agents/ v1 copies
