---
id: 1079
title: 'B-19: orchestration skill rewrite — w-orchestration/SKILL.md'
status: todo
priority: important
created: 2026-04-21T10:50:12.228673+00:00
updated: 2026-04-21T10:50:12.228673+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
parent: 1044
depends_on:
- 1076
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.3 algorithm
Module: `share/skills/w-orchestration/SKILL.md`

Rewrite the Wave Assembly section of the orchestration skill to reference the new engine-native `pick_tasks` API (AgentView.pick_tasks) instead of the hand-rolled dispatch logic. The skill must document: the 4-step pipeline (filter → sort → greedy wave assembly → return), the three wave constraints (size, dep-disjointness, agent-compatibility), default parameters (wave_size from config, max_waves=3), and the PickTasksResponse/DispatchEntry shapes.

This is a documentation-only task — no Python code changes.

## Acceptance Criteria

- [ ] w-orchestration/SKILL.md Wave Assembly section references `pick_tasks` MCP tool (not hand-rolled logic)
- [ ] Documents the 4-step algorithm: filter, sort, wave assembly, return
- [ ] Documents three wave constraints: size, dep-disjointness, agent-compatibility (D62+D63)
- [ ] Documents default wave_size (BoardConfig.wave_size) and max_waves=3
- [ ] Documents DispatchEntry shape including computed `agent` field
- [ ] Removes any legacy dispatch-loop logic that `pick_tasks` replaces
- [ ] No Python code changes in this task