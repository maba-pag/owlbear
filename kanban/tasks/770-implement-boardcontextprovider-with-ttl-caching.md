---
id: 770
title: Implement BoardContextProvider with TTL caching
status: backlog
priority: important
created: 2026-03-13T10:39:59.0640782+01:00
updated: 2026-03-13T14:16:40.5382359+01:00
started: 2026-03-13T11:21:24.3555851+01:00
tags:
    - agent
    - knowledge
    - scope:core
claimed_by: researcher
claimed_at: 2026-03-13T14:16:40.5382359+01:00
class: standard
---

Create a BoardContextProvider service that runs 'kanban-md list --compact --status in-progress --status review --status todo' and caches the result with configurable TTL (default 60s). Graceful degradation on subprocess failure. See docs/research/compact-board-context.md S4.
