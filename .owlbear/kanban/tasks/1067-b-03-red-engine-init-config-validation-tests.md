---
id: 1067
title: 'B-03: RED — engine init + config validation tests'
status: todo
priority: needed
created: 2026-04-21T10:47:58.331777+00:00
updated: 2026-04-21T10:47:58.331777+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1066
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.3 (BoardConfig), §3.6 (init errors), §6 (D24, D29, D33, D50, D65)
Module: `serve/kanban/tests/test_engine_init.py`

Test KanbanEngine.__init__ and BoardConfig validation. Covers config-time error detection: entry_status validation (D50), terminal_status validation (D65), agent_map coverage (D24), claim_timeout format (D29), agent_compatibility symmetry (D63), statuses/priorities enum presence.

## Acceptance Criteria

- [ ] AC-NEW-14: Engine init with `entry_status` not in `statuses` → ConfigError(ERR_ENTRY_STATUS_INVALID)
- [ ] AC-NEW-23: Engine init with `terminal_status` not in `statuses` OR not equal to `statuses[-1]` → ConfigError(ERR_TERMINAL_STATUS_INVALID)
- [ ] Agent_map missing a declared status → ConfigError at init per D24
- [ ] Malformed claim_timeout → ConfigError(ERR_INVALID_CLAIM_TIMEOUT) per D29
- [ ] Agent_compatibility not symmetric → ConfigError at init per D63
- [ ] Valid config constructs engine + AgentView + CockpitView stubs without error
- [ ] Engine has no `agent_name` constructor parameter per D33
- [ ] All tests fail (RED phase)