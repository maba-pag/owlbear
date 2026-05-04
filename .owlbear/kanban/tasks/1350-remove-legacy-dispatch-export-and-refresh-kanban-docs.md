---
id: 1350
title: Remove legacy dispatch export and refresh kanban docs
status: backlog
priority: needed
created: 2026-05-04T18:27:23.261100+00:00
updated: 2026-05-04T18:27:23+00:00
tags:
- sync-blocker
- kanban
- docs
- api-contract
parent:
depends_on:
- 1342
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

`pick_dispatchable()` is deprecated in favor of `AgentView.pick_tasks()`, but it is still exported from `owlbear_kanban.__all__` and protected by tests. The package README also contains stale raw-engine examples that no longer match current signatures. Because `serve/kanban/README.md` is consumer-facing and synced to main, the package should not ship with broken examples or protected legacy API drift.

Audit decision: remove or explicitly quarantine the deprecated dispatch API and refresh the package README before sync.

## Acceptance Criteria

1. Audit first-party imports and real callers of `pick_dispatchable()`.
2. If no active first-party caller requires it, remove `pick_dispatchable` from `owlbear_kanban.__all__` and root-package exports.
3. If a temporary compatibility path is still required, keep it only behind an explicit deprecation/quarantine decision and update tests to assert that limited contract.
4. Update or remove tests that currently require `pick_dispatchable` to remain in `__all__` as a normal public export.
5. Refresh `serve/kanban/README.md` examples so they match current `KanbanEngine` and `AgentView` signatures.
6. Remove the stale `pick_dispatchable(tasks)` README example or replace it with `AgentView.pick_tasks()` usage.
7. Ensure README mutation examples do not advertise nonexistent raw-engine parameters such as `tags=` on `edit_task`.
8. Run package export tests and documentation/API smoke tests after the change.

## Key Files

- `serve/kanban/src/owlbear_kanban/__init__.py`
- `serve/kanban/src/owlbear_kanban/dispatch.py`
- `serve/kanban/README.md`
- `tests/test_init_exports_1213.py`
- `tests/test_dispatch_gate_port_1214.py`
- `tests/test_cockpit_boundary.py`

## Audit Evidence

- `pick_dispatchable()` emits `DeprecationWarning`, but root package exports still include it.
- `tests/test_init_exports_1213.py` still enforces the deprecated root export.
- `serve/kanban/README.md` documents `pick_dispatchable(tasks)` even though the implementation takes a `KanbanEngine`.
- `serve/kanban/README.md` shows raw engine edit examples that do not match the current `edit_task` signature.

## Source

Deployment audit finding group 7, 2026-05-04.
