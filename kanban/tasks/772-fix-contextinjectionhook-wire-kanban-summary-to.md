---
id: 772
title: 'Fix ContextInjectionHook: wire kanban_summary to system prompt'
status: backlog
priority: nice-to-have
created: 2026-03-13T10:40:31.8341587+01:00
updated: 2026-03-13T14:23:22.7928429+01:00
started: 2026-03-13T14:09:46.3517339+01:00
tags:
    - agent
    - scope:core
    - bug
claimed_by: researcher
claimed_at: 2026-03-13T14:23:22.7928429+01:00
class: standard
---

ContextInjectionHook stores kanban_summary in event data['context'] but this is NOT wired into the agent system prompt. Either remove the dead code or wire it through. See docs/research/compact-board-context.md S3.3.

[[2026-03-13]] Fri 14:22
## Research
- Doc: docs/research/context-injection-hook-dead-code.md
- Both outputs (instructions, kanban_summary) are dead: zero readers in src/
- instructions redundant with ContextManager (DRY violation)
- kanban_summary superseded by BoardContextProvider (#770/#771)
- Recommendation (.90): Remove hook entirely (Option A)
- Follow-up: #779 (Remove dead ContextInjectionHook) at ideation
- Confidence: .90
