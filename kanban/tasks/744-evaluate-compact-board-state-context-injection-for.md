---
id: 744
title: Evaluate compact board-state context injection for agents
status: ideation
priority: nice-to-have
created: 2026-03-11T21:17:18.1414264+01:00
updated: 2026-03-12T15:14:42.895444+01:00
started: 2026-03-12T08:38:53.5327917+01:00
tags:
    - research
    - agent
    - knowledge
class: standard
---

Investigate injecting a compressed kanban board snapshot into agent system prompts for situational awareness. Compare MC's generate-context.ts approach (~650 tokens) vs piping kanban-md list --compact output. Determine if KnowledgeQueryService is the right injection point. See docs/research/mission-control-research.md S3.2 and S4.
