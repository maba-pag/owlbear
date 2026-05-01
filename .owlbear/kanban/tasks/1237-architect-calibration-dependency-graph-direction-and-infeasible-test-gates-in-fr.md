---
id: 1237
title: 'Architect calibration: dependency-graph direction and infeasible test gates
  in frontend refactor AC'
status: backlog
priority: important
created: 2026-05-01T02:10:20.377775+00:00
updated: 2026-05-01T02:10:39.095735+00:00
tags:
- calibration
- architect
- ac-quality
- frontend
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Spawned from task #1225 (KanbanBoard split into Card/Column/Board components). AC quality scored 3/5. Two defects required full architect re-review and a second pipeline cycle.

## Defect 1 — Inverted dependency-graph direction

AC Line 3 specified that `KanbanBoard.tsx` should import `Card` directly. The correct dependency chain is `KanbanBoard → Column → Card` (Board owns Columns; Columns own Cards). The AC inverted this, making `KanbanBoard → Card` a direct import — which bypasses Column and collapses the intended layering.

The implementation was architecturally correct; the AC was wrong. The reviewer correctly failed the task, triggering an avoidable cycle.

## Defect 2 — Infeasible must-pass gate (pre-existing red suite)

AC Line 6 named `test_cockpit_react_compiler_1015.py` as a must-pass gate. That suite had 4 pre-existing failures (vite/package config + E2E) that predate task #1225. Naming an already-red suite as a hard gate made the gate infeasible on a green implementation, causing reviewer FAIL.

## Acceptance Criteria

1. Architect produces a written calibration note (appended to this task body or as a `.owlbear/decisions/` entry) covering:
   a. **Dependency-graph direction rule:** For frontend component AC, always trace the `parent → child` ownership chain from live code before writing import-shape constraints. AC must name the correct importer and importee based on the actual component hierarchy.
   b. **Suite health pre-check rule:** Before naming a durable test suite as a must-pass gate in AC, run or inspect the suite to confirm it is currently green. If the suite has pre-existing failures unrelated to the task, either (a) exclude the failing tests from the gate with an explicit note, or (b) name a scoped subset of the suite that is known-green.
2. Calibration note references task #1225 as the triggering case.
3. Follow-up kanban tasks are created if either rule requires a systemic fix (e.g., a checklist update to the architect skill or brief template).