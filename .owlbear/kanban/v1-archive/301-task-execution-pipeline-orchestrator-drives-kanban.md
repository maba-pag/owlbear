---
id: 301
title: Task execution pipeline — orchestrator drives kanban-based work
status: archived
priority: critical
created: 2026-03-01T02:53:37.8647697+01:00
updated: 2026-03-01T17:09:26.1644003+01:00
started: 2026-03-01T06:23:01.6171498+01:00
completed: 2026-03-01T17:09:26.1644003+01:00
tags:
    - phase-12
    - agent
    - orchestrator
depends_on:
    - 296
class: standard
---

SPLIT into atomic sub-tasks:

- #313 — KanbanToolset unit tests (TDD first) [todo]
- #314 — KanbanToolset implementation — 7 async subprocess tools [backlog, depends-on #313]
- #315 — Wire KanbanToolset into bootstrap + orchestrator definition [backlog, depends-on #314]
- #316 — Orchestrator kanban pipeline prompt + integration test [backlog, depends-on #315]

Architect decision: Follow GitLocalToolset pattern exactly — async subprocess wrapper, FunctionToolset subclass, 7 tools (list, show, create, move, edit, pick, context). --no-color and --dir on every command. Mutating ops emit PRE_TOOL_USE hooks. Error handling via string returns, never exceptions. See docs/research/kanban-toolset.md.

This parent task is now complete — all work tracked via children.
