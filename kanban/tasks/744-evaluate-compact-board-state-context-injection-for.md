---
id: 744
title: Evaluate compact board-state context injection for agents
status: backlog
priority: nice-to-have
created: 2026-03-11T21:17:18.1414264+01:00
updated: 2026-03-13T10:42:08.3982378+01:00
started: 2026-03-12T08:38:53.5327917+01:00
tags:
    - research
    - agent
    - knowledge
claimed_by: researcher
claimed_at: 2026-03-13T10:42:08.3982378+01:00
class: standard
---

Investigate injecting a compressed kanban board snapshot into agent system prompts for situational awareness. Compare MC's generate-context.ts approach (~650 tokens) vs piping kanban-md list --compact output. Determine if KnowledgeQueryService is the right injection point. See docs/research/mission-control.md S3.2 and S4.

[[2026-03-13]] Fri 09:12

## AC
- [ ] Research doc at docs/research/compact-board-context.md
- [ ] Compare MC's generate-context.ts (~650 tokens) vs kanban-md list --compact piping
- [ ] Evaluate KnowledgeQueryService as injection point
- [ ] Recommendation with confidence score
- [ ] Follow-up kanban tasks if warranted

[[2026-03-13]] Fri 10:42
## Research
- Doc: docs/research/compact-board-context.md
- MC's generate-context.ts compresses workspace state to ~650 tokens as static file
- kanban-md list --compact (active only) achieves ~220 tokens with real-time data
- KnowledgeQueryService is NOT the right injection point (wrong concern: vector search vs static board state)
- Recommendation (.80): BoardContextProvider with TTL cache, wired to turn() instructions
- Follow-ups: #770 (provider), #771 (wiring), #772 (fix ContextInjectionHook dead code)
