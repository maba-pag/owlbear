---
id: 1342
title: Curate stale pick_tasks RED suite after clarity-gate integration
status: backlog
priority: needed
created: 2026-05-04T15:10:47.698484+00:00
updated: 2026-05-04T17:28:16+00:00
tags:
- sync-blocker
- kanban
parent:
depends_on:
- 1343
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

The older `serve/kanban/tests/test_engine_pick_tasks_1074.py` suite is stale after TDD and clarity gates were integrated into dispatch. Many failures are caused by fixtures that no longer satisfy current dispatch eligibility, not by proven wave-assembly bugs.

`pick_tasks()` remains deployment-critical because it decides what work agents can start, but builders must repair the stale test layer before changing the algorithm.

## Acceptance Criteria

1. Audit every failing test in `serve/kanban/tests/test_engine_pick_tasks_1074.py` against the current clarity/TDD dispatch contract.
2. Fixtures intended to reach wave assembly include bullet or numbered AC lines.
3. In-progress fixtures intended to reach wave assembly include `## Test-Writer Notes` unless the current contract explicitly exempts them.
4. Tests that contradict the clarity gate are rewritten or deleted.
5. After fixture repair, any remaining failure is isolated as a focused algorithm contract with a clarity-compliant fixture.
6. `tests/test_dispatch_gate_port_1214.py` remains green.
7. No algorithm changes are made unless a live failure remains after stale fixtures are corrected.

## Key Files

- `serve/kanban/src/owlbear_kanban/agent_view.py`
- `serve/kanban/src/owlbear_kanban/dispatch.py`
- `serve/kanban/tests/test_engine_pick_tasks_1074.py`
- `tests/test_dispatch_gate_port_1214.py`

## Audit Evidence

- `serve/kanban/tests/test_engine_pick_tasks_1074.py` currently has failing tests, but many fixtures use prose-only task bodies and are now correctly excluded by the clarity gate.
- The newer clarity/TDD dispatch suite `tests/test_dispatch_gate_port_1214.py` passes 21/21, including a clarity-compliant bucket-compatibility regression.
- Current `AgentView.pick_tasks()` already delegates to dispatch TDD/clarity predicates and implements wave size, direct dependency-edge disjointness, and symmetric bucket compatibility.

## Source

Deployment audit reconciliation, 2026-05-04.