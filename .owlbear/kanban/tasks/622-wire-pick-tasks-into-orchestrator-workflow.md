---
id: 622
title: Wire pick_tasks into orchestrator workflow
status: backlog
priority: needed
created: 2026-04-05T01:31:13.8750468+02:00
updated: 2026-04-05T10:43:38.1327923+02:00
tags:
    - scope:agents
    - scope:orchestrator
    - phase-2
    - type:build
parent: 619
depends_on:
    - 621
class: standard
---

## Acceptance Criteria

- w-orchestration skill (share/skills/w-orchestration/SKILL.md) updated:
  - Step 1 (Plan) calls `pick_tasks` MCP tool directly instead of dispatching to dispatcher subagent
  - The subagent table removes dispatcher entry
  - Limit passed as parameter to pick_tasks
  - Status → agent mapping added to orchestrator's workflow (moved from dispatcher)
  - Crash failure exclusion logic added to orchestrator's own wave assembly / dispatch loop
- w-dispatch-planning skill (share/skills/w-dispatch-planning/SKILL.md) updated:
  - Header/description marks it as archived/reference-only
  - OR file moved to docs/research/ as historical design doc
- Orchestrator no longer calls dispatcher as a subagent
- pick_tasks tool call replaces the entire dispatcher subagent invocation

[[2026-04-05]]
## Research
- Research doc: .owlbear/research/wire-pick-tasks-orchestrator.md
- Sources: 9 studied, 7 high-relevance (all codebase-internal)
- Recommendation: Wire pick_tasks with status→agent mapping, DECOMP post-filter via show_task, tag passthrough param, drop gate_warnings (confidence: .82)
- Follow-up tasks created: #628 (update #621 AC for tag param, ideation), #629 (clean up dispatcher references, ideation)
- Decision requests: none — all findings T1/T2

## Challenge Results
- Challenger: RECONSIDER (items 3 and 4)
- Confidence in original: .75 → revised to .82
- Key challenges: (1) needs_decomp field changes #621 AC unnecessarily — use show_task post-filter instead; (2) scope param leaks orchestrator concepts — use tag passthrough instead; (3) missing first-stale detection state tracking
- Researcher response: accepted all three — revised DECOMP to post-filter, scope to tag passthrough, added last_dispatched state tracking to recommendation

[[2026-04-05]] Sun 10:43
Research complete. Doc at .owlbear/research/wire-pick-tasks-orchestrator.md. Key findings: 8 responsibilities migrated from dispatcher, 2 design gaps identified (DECOMP routing, scope filtering) with revised solutions after challenger review. Follow-ups: #628 (tag param AC update), #629 (dispatcher reference cleanup).
