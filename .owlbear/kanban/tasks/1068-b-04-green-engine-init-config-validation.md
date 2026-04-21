---
id: 1068
title: 'B-04: GREEN — engine init + config validation'
status: todo
priority: critical
created: 2026-04-21T10:48:09.323285+00:00
updated: 2026-04-21T10:48:09.323285+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1067
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.3, §3.6, §5, §6
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement KanbanEngine.__init__ with BoardConfig validation and role-view construction. This is the fork point: reads track (B-05/B-06) and writes track (B-07/B-08) both start from this task.

BoardConfig fields: statuses, priorities, entry_status (D50), terminal_status (D65), agent_map (D24), agent_types + agent_compatibility (D62/D63), claim_timeout (D29), wave_size, status_predicates (D15), archival_reasons (D37 frozen set).

Role views: AgentView and CockpitView facades (method stubs only — implementations in later tasks).

## Acceptance Criteria

- [ ] All RED tests from B-03 (#1067) pass
- [ ] BoardConfig is Pydantic model with all fields validated at init
- [ ] `entry_status` defaults to "research", validated in `statuses`
- [ ] `terminal_status` defaults to "done", validated as `statuses[-1]`
- [ ] `agent_map` must cover all `statuses` keys (D24 fail-fast)
- [ ] `claim_timeout` parsed from `Ns/Nm/Nh/Nd` string (D29)
- [ ] `agent_compatibility` validated as symmetric (D63)
- [ ] AgentView and CockpitView constructed at init with method stubs
- [ ] MigrationRequiredError raised if active tasks carry `claimed_by` frontmatter