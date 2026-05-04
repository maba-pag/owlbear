---
id: 1343
title: 'Complete engine config validation: entry_status, terminal_status, agent_map,
  compatibility'
status: todo
priority: needed
created: 2026-05-04T15:10:51.036581+00:00
updated: 2026-05-04T15:11:11.914799+00:00
tags:
- sync-blocker
- kanban
- config
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

`serve/kanban/tests/test_engine_init_1067.py` has 15 red tests verifying config validation behaviors. The engine constructor and config model are missing several validation checks that were designed but not implemented.

The init/config validation ensures the engine has a consistent, valid configuration before running — prerequisite for lifecycle contract correctness.

## Acceptance Criteria

1. `entry_status` not in config.pipeline.statuses → raises `ConfigError(ERR_ENTRY_STATUS_INVALID)` (case-sensitive, rejects empty string)
2. `terminal_status` must be in statuses AND equal statuses[-1] — not first, not middle
3. `agent_map` must have entries for ALL declared statuses (D24)
4. `agent_compatibility` must be symmetric (D63) — if A→B allowed, B→A must be allowed; else raises
5. `claim_timeout` accepts extended format (1h, 30s, 2d) (D29)
6. Engine constructor has NO `agent_name` parameter (D33)
7. `terminal_status` is a Pydantic model field with default "done" (D65)
8. `archival_reasons` is a frozenset, not list (D37)
9. AgentView has `pick_tasks` method (stub or full)
10. All 15 tests in `test_engine_init_1067.py` pass
11. No regression in passing engine/config tests

## Key Files

- `serve/kanban/src/owlbear_kanban/engine.py` (constructor, validation)
- `serve/kanban/src/owlbear_kanban/config_loader.py` (model fields, validators)
- `serve/kanban/tests/test_engine_init_1067.py`

## Dependencies

None — but #1339 (lifecycle reconciliation) depends on THIS being done first. Config must be valid before lifecycle behavior is reconciled.

## Source

Research: `.owlbear/research/kanban-mcp-deployment-audit.md`