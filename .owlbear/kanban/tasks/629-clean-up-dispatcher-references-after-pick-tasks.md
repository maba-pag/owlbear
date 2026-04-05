---
id: 629
title: Clean up dispatcher references after pick_tasks migration
status: ideation
priority: important
created: 2026-04-05T10:42:19.8702275+02:00
updated: 2026-04-05T10:42:19.8702275+02:00
tags:
    - scope:agents
    - phase-2
    - type:docs
parent: 619
depends_on:
    - 622
class: standard
---

## Acceptance Criteria

- `share/instructions/agent-common.instructions.md`: remove dispatcher row from Per-Agent Section Mapping table
- `share/skills/r-pipeline-protocol/SKILL.md`: update "the dispatcher will dispatch the planner" reference (line ~95) to reflect orchestrator handling DECOMP routing
- `share/skills/r-pipeline-protocol/SKILL.md`: update "blocked for triage by dispatcher" reference (line ~180) to reflect new owner
- `share/agents/README.md`: remove/update dispatcher from T1 Orchestrator tier row
- `share/skills/h-agent-structure/SKILL.md`: remove dispatcher from T1 Orchestrator tier row
- `share/agents/dispatcher.agent.md`: add deprecated header OR delete file

## Context

After #622 wires pick_tasks into the orchestrator, these cross-cutting references to the dispatcher agent become stale. See .owlbear/research/wire-pick-tasks-orchestrator.md.
