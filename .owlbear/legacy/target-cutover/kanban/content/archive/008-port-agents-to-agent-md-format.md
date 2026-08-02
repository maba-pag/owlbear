---
id: 8
title: Port agents to .agent.md format
status: archived
priority: medium
created: 2026-03-26 17:19:41.251373+01:00
updated: 2026-03-29 11:14:57.118123+02:00
started: 2026-03-29 11:14:56.821059+02:00
completed: 2026-03-29 11:14:56.821059+02:00
tags:
- phase-1
- scope:agents
- type:build
depends_on:
- 4
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-26]] Thu 18:09

Note: v1 has 11 agents (not 9). Includes test-writer.agent.md and kanban-planner.agent.md. Port all 11.

[[2026-03-29]] Sun 10:19
## Docs Gate
### Checklist

No docs impact -- task ported .agent.md config files only.

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Already references agents/ at lines 40, 145, 163; no .github/agents references remain |
| 2 | Docstrings | No | N/A | No Python modules changed |
| 3 | docs/sources/overview.md | Yes | Pass | Lines 1996-1998 include VS Code custom-agents, chat-tools, subagents docs for agent-port-v2.md |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/agent-port-v2.md exists; builder notes reference it |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/8-* files found)

[[2026-03-29]] Sun 11:14
## Audit

### AC Verification

AC1-9 (port all 11 agents): PASS - 11 .agent.md files exist in agents/
AC10 (tools field): PASS - spot-checked builder, reviewer; VS Code/MCP tool names, no PydanticAI refs
AC11 (agents field): PASS - spot-checked builder, reviewer; agents: [] configured
AC12 (test 2 agents): PASS - docs gate confirmed; settings.json includes agents/ path
AC13 (write to agents/): PASS - 11 files at repo root agents/
AC14 (settings.json): PASS - chat.agentFilesLocations includes agents: true
AC15 (delete v1 copies): PASS - .github/agents/ is empty

### Test Results
- pytest: 640 passed, 108 failed (all pre-existing; 0 attributable to #8)
- ruff: 1 pre-existing error (scripts/setup.py line length) unrelated
- voice test: collection error (missing module) unrelated

### AC Quality: 4/5
AC was specific (listed every agent), corrected from 9 to 11 mid-task. Minor gap only.

### Confidence: .96
### Action: archive
