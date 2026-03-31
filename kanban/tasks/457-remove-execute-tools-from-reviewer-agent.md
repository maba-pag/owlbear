---
id: 457
title: Remove execute/* tools from reviewer agent
status: ideation
priority: nice-to-have
created: 2026-03-30T23:47:55.0036687+02:00
updated: 2026-03-30T23:47:55.0036687+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 264
class: standard
---

Remove all 7 execute/* tools and read/terminalLastCommand from reviewer.agent.md. Update code-review skill to use MCP kanban tools instead of terminal kanban-md.exe commands. Document MCP-based handoff pattern as alternative to terminal handoff. See docs/research/reviewer-execute-tool-removal.md for full analysis.

AC:
- [ ] reviewer.agent.md tools list contains no execute/* entries
- [ ] reviewer.agent.md tools list does not contain read/terminalLastCommand
- [ ] reviewer.agent.md tools list retains: vscode/memory, read/problems, read/readFile, read/viewImage, agent, search, owlbear-kanban/*
- [ ] code-review skill Steps 1, 8, 9 reference MCP kanban tools instead of terminal kanban-md.exe commands
- [ ] code-review skill documents MCP-based handoff pattern (edit_task block+append then edit_task release)
- [ ] code-review skill Steps 3-5 reference Quality-Runner only (no direct terminal fallback)

Depends on: #264 (Quality-Runner wired in)
