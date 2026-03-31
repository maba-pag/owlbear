---
id: 317
title: Evaluate execute/* tool removal from reviewer agent
status: backlog
priority: nice-to-have
created: 2026-03-30T20:32:19.1638978+02:00
updated: 2026-03-30T23:48:42.8383188+02:00
tags:
    - scope:agents
    - phase-2
class: standard
---

After Quality-Runner is wired in and validated, evaluate whether the reviewer agent can drop execute/* tools entirely. The reviewer only uses terminal for pytest and ruff — both now handled by Quality-Runner. Removing execute/* tools would enforce the read-only boundary more strictly. Requires validation that no edge-case terminal usage exists. See docs/research/quality-runner-wiring.md.

[[2026-03-30]] Mon 23:48
## Research
Full analysis: docs/research/reviewer-execute-tool-removal.md

**Verdict (.80 confidence):** Remove all 7 execute/* tools + read/terminalLastCommand.
- pytest/ruff/coverage replaced by Quality-Runner subagent
- kanban-md.exe replaced by owlbear-kanban/* MCP tools (full parity confirmed)
- execute/runTests was explicitly forbidden by skill (deadlocks) yet still listed
- Subagent tools are independent of parent (VS Code docs confirmed)
- Parallel fan-out (#265) compatible with removal

**Follow-up tasks created:**
- #457 Remove execute/* tools from reviewer agent (depends on #264)
- #458 Test: Remove execute/* tools from reviewer agent (depends on #457)

[[2026-03-30]] Mon 23:48
## Research
Full analysis: docs/research/reviewer-execute-tool-removal.md

**Verdict (.80 confidence):** Remove all 7 execute/* tools + read/terminalLastCommand.
- pytest/ruff/coverage replaced by Quality-Runner subagent
- kanban-md.exe replaced by owlbear-kanban/* MCP tools (full parity confirmed)
- execute/runTests was explicitly forbidden by skill (deadlocks) yet still listed
- Subagent tools are independent of parent (VS Code docs confirmed)
- Parallel fan-out (#265) compatible with removal

**Follow-up tasks created:**
- #457 Remove execute/* tools from reviewer agent (depends on #264)
- #458 Test: Remove execute/* tools from reviewer agent (depends on #457)
