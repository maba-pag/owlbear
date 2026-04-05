---
id: 458
title: 'Test: Remove execute/* tools from reviewer agent'
status: ideation
priority: nice-to-have
created: 2026-03-30T23:48:03.5381382+02:00
updated: 2026-03-30T23:48:03.5381382+02:00
tags:
    - scope:agents
    - phase-2
    - test
depends_on:
    - 457
class: standard
---

Test task for #457. Verify execute/* tool removal and MCP kanban migration in reviewer agent.

AC:
- [ ] Test verifies reviewer.agent.md contains no execute/* tools
- [ ] Test verifies reviewer.agent.md does not contain read/terminalLastCommand
- [ ] Test verifies reviewer.agent.md retains required 7 tool entries (vscode/memory, read/problems, read/readFile, read/viewImage, agent, search, owlbear-kanban/*)
- [ ] Test verifies code-review skill references MCP kanban tools for task operations
- [ ] Test verifies code-review skill does not reference kanban-md.exe terminal commands
- [ ] All tests fail before #457 implementation (RED phase)

Patterns to follow: tests/test_disable_model_invocation.py
