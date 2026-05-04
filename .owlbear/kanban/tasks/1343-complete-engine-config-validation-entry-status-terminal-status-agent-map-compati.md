---
id: 1343
title: 'Config validation cleanup: remove agent_name while preserving lazy agent_map'
status: backlog
priority: needed
created: 2026-05-04T15:10:51.036581+00:00
updated: 2026-05-04T17:28:16+00:00
tags:
- sync-blocker
- kanban
- config
- cockpit
parent:
depends_on:
- 1336
- 1351
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Most old engine-init config validation expectations are now implemented or intentionally superseded by lazy dispatch validation. The remaining deployment-relevant work is D33: remove the stale `agent_name` constructor parameter while preserving lazy `agent_map` behavior for Cockpit and other non-dispatch consumers.

## Acceptance Criteria

1. Remove `agent_name` from `KanbanEngine.__init__`.
2. Update every first-party caller, test, and benchmark that still passes `agent_name`, including Cockpit launch wiring.
3. Preserve deterministic Cockpit activity/source labeling through explicit `source="cockpit"` mutation calls or an approved replacement, not constructor state.
4. Preserve lazy `agent_map` validation: empty/incomplete `agent_map` must not fail engine construction when dispatch is not being used.
5. `AgentView.pick_tasks()` continues to raise the appropriate config error when dispatch needs missing `agent_map` entries.
6. Replace stale `test_engine_init_1067.py` assertions that require eager `agent_map` validation with tests for the lazy dispatch contract.
7. Keep already-green semantic config tests for entry status, terminal status, claim timeout, archival reason type, and symmetric compatibility.
8. Run config, lazy-agent-map, Cockpit launch/read/mutation, and engine-init tests together before completion.

## Key Files

- `serve/kanban/src/owlbear_kanban/engine.py`
- `serve/kanban/src/owlbear_kanban/models.py`
- `serve/kanban/src/owlbear_kanban/agent_view.py`
- `serve/cockpit/src/owlbear_cockpit/main.py`
- `serve/kanban/tests/test_engine_init_1067.py`
- `tests/test_engine_lazy_agent_map_1221.py`
- `tests/test_cockpit_launch.py`

## Audit Evidence

- `serve/kanban/tests/test_engine_init_1067.py` now has 13 passed / 4 failed, not 15 broad failures.
- Entry status, terminal status, claim timeout, archival reason type, AgentView existence, and symmetric compatibility are already implemented.
- The old eager `agent_map` init failures conflict with current lazy validation and Cockpit's ability to start with `agent_map: {}`.
- User decision during deployment audit: keep D33 and remove `agent_name`, despite current Cockpit/tests still using it.

## Source

Deployment audit reconciliation, 2026-05-04.