---
id: 622
title: Wire pick_tasks into orchestrator workflow
status: ideation
priority: needed
created: 2026-04-05T01:31:13.8750468+02:00
updated: 2026-04-05T01:58:34.9462465+02:00
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
