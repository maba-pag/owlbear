---
id: 1743
title: Cockpit post-edit-action visual sweep
status: archived
priority: medium
created: 2026-05-23T10:40:45+0200
updated: 2026-05-24T10:50:01.857286+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-sweep
parent:
depends_on:
  - 1741
  - 1742
ac:
  - Capture current desktop screenshots for Kanban, Decisions, Memory, and Ideas
    after the task-detail and memory edit-action fixes.
  - Record geometry metrics for workspace bounding, overflow, scroll surfaces,
    and obvious action reachability.
  - Classify any finding as observed/theoretical and current/future harm before
    creating a fix task.
  - Create a follow-up task before editing any newly discovered issue.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Problem
Task detail and Memory edit workflows now have dedicated action visibility fixes. The primary Cockpit tabs need a fresh runtime sweep so the next polish task is based on current screenshots and metrics rather than stale evidence.

## Evidence
- Screenshots:
  - `.owlbear/scratch/1716-wide-cockpit/1743-kanban-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1743-decisions-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1743-memory-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1743-ideas-desktop.png`
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1743-current-tabs-metrics.json`.
- Stable surfaces: Kanban, Decisions, Memory, and Ideas all reported no document-level horizontal or vertical overflow, and all workspaces stayed within the 1440x1000 viewport.
- Observed finding: the Kanban Done lane contains more cards than the visible column body can show, and the first viewport shows a cut-off trailing card without an explicit continuation affordance.
- Classification: observed current interaction usability issue. Current harm is mild but real: users can scroll the lane, but the clipped card reads as an abrupt cutoff rather than an intentional scroll surface. Product value is high enough to fix because Kanban is the primary Cockpit work surface and long lanes are common.
- Follow-up fix task created: #1744 Add Kanban column scroll affordance.