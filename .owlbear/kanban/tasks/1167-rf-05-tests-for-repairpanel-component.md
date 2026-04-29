---
id: 1167
title: 'RF-05: Tests for RepairPanel component'
status: backlog
priority: nice-to-have
created: 2026-04-28T17:38:24.640853+00:00
updated: 2026-04-28T17:40:41.112412+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:test
parent:
depends_on:
- 1166
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Seed from ideation task #1042 — cockpit repair flow feature.
RepairPanel renders in the HealthBadge detail panel. Uses Porsche Design System components.
Wires to `useRepairFlow` hook (#1166) for state management.

## Acceptance Criteria

- [ ] Test: "Repair" button renders when corruption count > 0
- [ ] Test: "Repair" button hidden when corruption count is 0
- [ ] Test: clicking "Repair" shows confirmation dialog with corruption count in message
- [ ] Test: confirming dialog triggers repair execution
- [ ] Test: cancelling dialog returns to button state
- [ ] Test: loading spinner shown during repair execution
- [ ] Test: results display groups outcomes by action (fixed/quarantined/failed sections)
- [ ] Test: each outcome row shows file path and detail when present
- [ ] Test: dismiss button in results view clears results and returns to button state

## Scope

- **In scope:** Component rendering tests with mocked hook, PDS component usage
- **Out of scope:** Hook implementation, API calls, Shell integration