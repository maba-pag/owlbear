---
id: 1166
title: 'RF-04: Implement useRepairFlow hook'
status: backlog
priority: nice-to-have
created: 2026-04-28T17:38:24.630886+00:00
updated: 2026-04-29T09:00:28.865516+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:build
parent:
depends_on:
- 1165
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Seed from ideation task #1042 — cockpit repair flow feature.
Implements the repair flow state machine hook.
Consumes `repairStorage()` (#1164). Accepts a re-poll callback to refresh scan data after repair.

## Acceptance Criteria

- [ ] `useRepairFlow` hook exported with state machine: idle → confirming → repairing → done/error
- [ ] Exposes: `requestRepair(count)`, `confirmRepair()`, `cancelRepair()`, `dismissResults()`, `state`, `outcomes`, `error`
- [ ] Groups outcomes by action (fixed/quarantined/failed) in done state
- [ ] Calls re-poll callback after successful repair
- [ ] All #1165 tests pass

## Scope

- **In scope:** Hook implementation, state management, API call orchestration
- **Out of scope:** Rendering, PDS components, Shell wiring
[[2026-04-29]]


## Superseded
Merged into #1165 by architect. Builder had already implemented both tests and hook in #1165. This task is redundant — do not process.
