---
id: 1352
title: Clean up activity attribution and legacy logger
status: backlog
priority: needed
created: 2026-05-04T18:45:18.968070+00:00
updated: 2026-05-04T18:45:09+00:00
tags:
- sync-blocker
- kanban
- audit-log
parent:
depends_on:
- 1348
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

The kanban package has two activity concepts: the current structured `ActivityEvent` / `activity_store.py` path that uses `source`, and an older `activity_log.py` helper that writes actor-shaped events. Tests explicitly assert that engine events do not include an `actor` field, so the issue is not simply to add actor back. The deployment risk is drift: unused logger code, stale docs/prose, and unclear source attribution across engine, MCP, and Cockpit.

Before sync, the activity/audit story should be one coherent contract: one logger model, one attribution vocabulary, and no legacy module inviting new callers to write incompatible audit rows.

## Acceptance Criteria

1. Confirm the canonical activity schema is `ActivityEvent` with `source`/`kind`/`task_id`/`detail`; do not reintroduce an `actor` field unless a decision request changes the contract.
2. Remove, quarantine, or clearly deprecate `serve/kanban/src/owlbear_kanban/activity_log.py` so new code cannot accidentally write incompatible actor-shaped events.
3. Engine, AgentView/MCP, and Cockpit activity sources are named consistently and are documented where activity logs are documented.
4. Any stale README, skill, or test wording that implies `actor` is canonical is updated to the `source` contract.
5. Tests cover that claim/release/edit/move events still write the canonical schema and that no production path imports the legacy logger.

## Key Files

- `serve/kanban/src/owlbear_kanban/activity_log.py`
- `serve/kanban/src/owlbear_kanban/activity_store.py`
- `serve/kanban/src/owlbear_kanban/models.py`
- `serve/kanban/src/owlbear_kanban/engine.py`
- `serve/kanban/src/owlbear_kanban/agent_view.py`
- `tests/test_engine_activity_session.py`

## Audit Evidence

- `activity_store.py` is the canonical append/read/compact implementation for `ActivityEvent`.
- `activity_log.py` still exists with actor-oriented event helpers.
- `tests/test_engine_activity_session.py` explicitly asserts engine-emitted events must not include `actor`, which means documentation/code cleanup must preserve the source-based contract rather than invent a second attribution model.

## Recommendation

Keep this as a sync blocker but lower than trust-boundary and MCP contract tasks. The deployment concern is audit consistency, not a proven live crash.

## Source

Meta-audit blind source pass, 2026-05-04.
