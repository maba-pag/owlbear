---
id: 1165
title: 'RF-03: Tests for useRepairFlow hook'
status: backlog
priority: nice-to-have
created: 2026-04-28T17:38:24.621390+00:00
updated: 2026-04-28T17:40:41.102635+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:test
parent:
depends_on:
- 1164
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Seed from ideation task #1042 — cockpit repair flow feature.
Hook manages the repair flow state machine: idle → confirming → repairing → done/error.
Consumes `repairStorage()` API client (#1164) and triggers scan re-poll on success.

## Acceptance Criteria

- [ ] Test: hook starts in idle state (no modal, no results)
- [ ] Test: `requestRepair(count)` transitions to confirming state with corruption count
- [ ] Test: `confirmRepair()` calls `repairStorage()` and transitions to repairing (loading) state
- [ ] Test: successful repair transitions to done state with grouped outcomes (fixed/quarantined/failed)
- [ ] Test: `cancelRepair()` returns to idle state from confirming
- [ ] Test: API error during repair transitions to error state with message
- [ ] Test: `dismissResults()` returns to idle from done or error state
- [ ] Test: hook triggers scan re-poll callback after successful repair

## Scope

- **In scope:** Hook state machine tests with mocked API client
- **Out of scope:** Rendering, PDS components, actual API calls