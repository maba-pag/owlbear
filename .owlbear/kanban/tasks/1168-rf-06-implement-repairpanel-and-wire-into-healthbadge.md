---
id: 1168
title: 'RF-06: Implement RepairPanel and wire into HealthBadge'
status: backlog
priority: nice-to-have
created: 2026-04-28T17:38:24.649104+00:00
updated: 2026-04-28T17:40:41.117117+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:build
parent:
depends_on:
- 1167
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Seed from ideation task #1042 — cockpit repair flow feature.
Implements the RepairPanel component and wires it into the HealthBadge detail panel.
Uses Porsche Design System components. Existing ConfirmDialog at `serve/cockpit/web/src/components/ConfirmDialog.tsx` may need type extension for repair confirmation.

## Acceptance Criteria

- [ ] RepairPanel component renders "Repair" button when corruption count > 0
- [ ] Click triggers confirmation dialog: "This will attempt to repair N corrupted files. Fixed files are restored, unfixable files are quarantined. Continue?"
- [ ] Loading state shown during POST /api/tasks/repair execution
- [ ] Results panel groups outcomes by action (fixed/quarantined/failed) with file paths and details
- [ ] Dismiss button clears results
- [ ] RepairPanel integrated into HealthBadge detail panel
- [ ] After successful repair, scan re-poll triggered to update badge count
- [ ] Uses PDS components (p-button, p-spinner, p-text, etc.)
- [ ] All #1167 tests pass

## Scope

- **In scope:** RepairPanel component, ConfirmDialog integration (extend type if needed), HealthBadge wiring
- **Out of scope:** Backend changes, new API endpoints, Shell layout changes