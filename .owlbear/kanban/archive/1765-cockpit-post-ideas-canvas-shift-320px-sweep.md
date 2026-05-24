---
id: 1765
title: Cockpit post Ideas canvas-shift 320px sweep
status: archived
priority: important
created: 2026-05-23T17:06:12.586171+02:00
updated: 2026-05-24T10:50:02.162994+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-proof
  - mobile
  - sweep
parent:
depends_on:
  - 1764
ac:
  - 'Re-run the 320px mobile interaction sweep after the #1764 PDS Canvas overflow
    fix.'
  - Confirm the Ideas dirty editor and preview no longer shift left in the full
    route sequence.
  - Re-check Memory edit, Decisions resolver, and Kanban task detail/edit for
    screenshot-confirmed current harm.
  - Classify any remaining finding as observed current harm, plan risk, or
    expected constrained behavior before creating a fix task.
  - Record screenshot and metric evidence under
    `.owlbear/scratch/1716-wide-cockpit/`.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Purpose
Run a fresh 320px mobile sweep after #1764 to verify the shell-level canvas fix holds in the broader Cockpit interaction sequence and to find the next screenshot-confirmed issue, if any.

## Evaluation Frame
- Screenshots decide product quality; geometry is supporting evidence.
- Expected Kanban horizontal board behavior is not a defect unless active workflows are clipped or unreachable.
- Create a follow-up fix task only for observed current harm.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1765-320px-post-canvas-shift-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1765-320px-post-canvas-shift-sweep-metrics.json`
- `.owlbear/scratch/1716-wide-cockpit/1765-320-ideas-dirty-editor.png`
- `.owlbear/scratch/1716-wide-cockpit/1765-320-ideas-dirty-preview.png`

## Result
- The #1764 canvas-shift fix holds in the full 320px route sequence: no metric issues, no document overflow, no failed requests, and `canvasRootLeftReset = true` across the sweep.
- Ideas dirty editor and dirty preview both keep `workspace.left = 16` and `ideasWorkspace.left = 16` at 320px.
- Memory edit, Decisions resolver, and Kanban task detail/edit remain constrained and reachable in screenshot review.
- Minor polish follow-up: #1766 switches Ideas toolbar controls to the PDS `PButton` icon API after the 320px dirty editor screenshot showed the Preview control as text-only.