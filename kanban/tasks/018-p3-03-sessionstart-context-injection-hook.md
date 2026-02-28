---
id: 18
title: 'P3-03: SessionStart context injection hook'
status: archived
priority: medium
created: 2026-02-24T15:11:11.4147194+01:00
updated: 2026-02-27T10:00:01.0620761+01:00
started: 2026-02-27T00:39:19.8415883+01:00
completed: 2026-02-27T10:00:01.0620761+01:00
tags:
    - phase-3
    - hooks
depends_on:
    - 16
    - 38
class: standard
---

PydanticAI SESSION_START hook that injects project context.

## AC
- ContextInjectionHook class in src/owlbear/core/hooks/ registered on SESSION_START
- Loads project purpose from copilot-instructions.md (configurable path)
- Runs kanban board context summary (kanban-md context or equivalent)
- Returns combined context as structured data for system prompt enrichment
- Follows URLSafetyGuard pattern: __call__(data), register(hooks) method
- Handles missing files gracefully (logs warning, continues with partial context)
- Tests: register, fire on session start, missing file handling, context format
- Depends on HookRegistry (#38, done)
