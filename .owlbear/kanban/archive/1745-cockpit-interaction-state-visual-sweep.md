---
id: 1745
title: Cockpit interaction-state visual sweep
status: archived
priority: medium
created: 2026-05-23T10:55:13+0200
updated: 2026-05-24T10:50:01.886730+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-sweep
parent:
depends_on:
  - 1744
ac:
  - Capture current desktop runtime evidence for at least the Decisions resolver
    and Ideas dirty/edit states after the
  - Record geometry metrics for visible action reachability, bounded scroll
    surfaces, document overflow, and console/page errors.
  - Classify each finding as observed/theoretical, current/future harm, and
    product value.
  - Create a follow-up fix task before editing any newly discovered issue.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Problem
The resting tab sweep is stable, but Cockpit still needs current browser evidence for important interaction states where usability issues often appear only after opening a resolver, editing content, or creating dirty state.

## Evidence Plan
- Capture a Decisions resolver open state with action buttons and modal bounds visible.
- Capture Ideas after making the editor dirty, with save/dirty state and preview/editor surfaces measured.
- Re-check document-level overflow and console/page errors across those interaction states.

## Evaluation Notes
## Evidence
- Screenshots:
  - `.owlbear/scratch/1716-wide-cockpit/1745-decisions-resolver.png`
  - `.owlbear/scratch/1716-wide-cockpit/1745-ideas-dirty-editor.png`
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1745-interaction-state-metrics.json`.
- Decisions resolver: no document-level horizontal or vertical overflow; modal surface is bounded inside the 1440x1000 viewport; Submit Decision and Close Modal are visible and reachable (`bottom: 855`).
- Ideas dirty editor: no document-level horizontal or vertical overflow; editor shell, dirty pill, preview toggle, Save action, and state panel are visible and reachable; editor remains bounded inside the workspace (`bottom: 960`).
- Browser noise: two `requestfailed` entries appeared after navigating away from long-lived/background requests (`/api/events` and `/api/tasks/scan`, both `net::ERR_ABORTED`). This is classified as expected navigation noise, not a user-facing Cockpit error.

## Evaluation Notes
- Decisions resolver classification: observed healthy current state. Current harm: none found in the captured desktop interaction state. Product value: validated primary decision workflow actions remain reachable.
- Ideas dirty editor classification: observed healthy current state. Current harm: none found in the captured desktop dirty/edit state. Product value: validated notebook save/preview controls and dirty feedback remain reachable.
- Follow-up: no desktop fix task created from this sweep. Next evidence target should be responsive/mobile behavior because the desktop resting and interaction states are now mostly bounded and usable.
