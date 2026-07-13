---
id: 1740
title: Task detail edit-mode visual sweep
status: archived
priority: medium
created: 2026-05-23T10:19:12+0200
updated: 2026-05-24T10:50:01.817413+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - visual-sweep
parent:
depends_on:
  - 1739
ac:
  - Capture current screenshots for task detail edit mode after the
  - Include normal edit mode and dirty/unsaved-change state where possible.
  - Record metrics for viewport fit, scroll reachability, control visibility,
    and document overflow.
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
The task detail display mode is now viewport-bounded and has a scroll affordance, but the edit form uses denser controls and the unsaved-change guard overlays the same modal. These interaction states need screenshot-backed verification before the task detail workflow can be considered polished.

## Evidence
- Captured edit-mode screenshots:
  - `.owlbear/scratch/1716-wide-cockpit/1740-task-detail-edit.png`
  - `.owlbear/scratch/1716-wide-cockpit/1740-task-detail-dirty.png`
  - `.owlbear/scratch/1716-wide-cockpit/1740-task-detail-unsaved-dialog.png`
- Metrics evidence: `.owlbear/scratch/1716-wide-cockpit/1740-task-detail-edit-sweep-metrics.json`.
- Stable surfaces: task detail modal remained viewport-bounded (`bottom: 950` at a 1000px viewport), the internal content region stayed vertical-only, and the unsaved-change dialog stayed contained inside the modal.
- Finding: edit mode placed Save/Cancel and dirty feedback below the first visible content viewport: `saveButton.top: 1451`, `cancelEditButton.top: 1451`, and dirty indicator `top: 1467` while content viewport ended at `bottom: 950`.
- Classification: observed current interaction usability issue. Current harm is that users can edit fields immediately but must scroll far down to complete or cancel the edit. Product value of fixing is high because task editing is a primary Cockpit workflow.
- Follow-up fix task created: #1741 Keep task detail edit actions visible.
