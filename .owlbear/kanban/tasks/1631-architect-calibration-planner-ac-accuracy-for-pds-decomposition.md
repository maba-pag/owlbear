---
id: 1631
title: 'Architect calibration: planner AC accuracy for PDS decomposition'
status: backlog
priority: nice-to-have
created: 2026-05-16T07:50:38.652054+00:00
updated: 2026-05-16T07:50:43.697264+00:00
tags:
  - process
parent:
depends_on: []
ac:
  - 'Audit covers all tasks decomposed from #1590, with per-task AC accuracy verdict
    (correct / inaccurate / not verifiable)'
  - Root-cause analysis distinguishes isolated error from systemic pattern
  - If systemic, a concrete planner process guard is proposed with expected 
    effectiveness
  - Follow-up tasks created for any corrective actions identified
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Review planner AC accuracy across the PDS decomposition batch (parent #1590) and identify systemic patterns that led to factually incorrect acceptance criteria.

## Context

During audit of #1605 (P1-07: Extend computeSignal with unknown state), two ACs were factually wrong:
- **AC-1** said "return an object with state 'unknown'" — but `computeSignal` returns a string, not an object.
- **AC-2** listed state names "green/yellow/red/gray/stale" — but actual engine states are `dr-pending/blocked/claimed/deps-unmet/ready`.

These ACs were written during planner decomposition of parent #1590. The architect correctly identified #1605 as superseded by #1599, but the original ACs would have misled an implementer had they reached a builder first.

This suggests the planner did not read the actual source code (`computeSignal` return type, engine status enum) before writing ACs — violating the "research before implementation" heuristic.

## Scope

1. Audit all tasks created in the #1590 decomposition batch for AC accuracy against actual codebase state at time of planning.
2. Identify whether the pattern is isolated to #1605 or systemic across the batch.
3. If systemic, propose a planner process guard (e.g., mandatory source-read step before AC authoring for refactor/extension tasks).
4. Create follow-up tasks for any corrective actions identified.