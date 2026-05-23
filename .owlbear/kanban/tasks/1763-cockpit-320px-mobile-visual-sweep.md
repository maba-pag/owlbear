---
id: 1763
title: Cockpit 320px mobile visual sweep
status: done
priority: important
created: 2026-05-23T16:50:10+0200
updated: 2026-05-23T16:53:08+0200
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-proof
  - mobile
  - sweep
parent:
depends_on: [1762]
ac:
  - Capture narrow 320px mobile Cockpit states after the #1762 clean sweep.
  - Include the core workspace routes and non-mutating interaction states most likely to reveal narrow-width clipping.
  - Confirm recent Memory edit and Ideas dirty toolbar fixes survive at 320px width.
  - Classify any new finding as observed current harm, plan risk, or theoretical before creating a fix task.
  - Record screenshot and metric evidence under `.owlbear/scratch/1716-wide-cockpit/`.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Purpose
Stress the current Cockpit UI at the 320px mobile floor. The 390px and desktop sweeps are clean; this pass checks whether compact mobile devices still preserve controls, route bounds, and recent fixes.

## Evaluation Frame
- Prefer screenshot-confirmed harm over raw geometry noise.
- Treat Kanban horizontal board content as expected only when the active lane and task/modal workflows remain reachable.
- Keep recent Memory edit and Ideas dirty-preview fixes under direct inspection.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1763-320px-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1763-320px-mobile-sweep-metrics.json`
- `.owlbear/scratch/1716-wide-cockpit/1763-320-ideas-dirty-editor.png`
- `.owlbear/scratch/1716-wide-cockpit/1763-320-ideas-dirty-preview.png`

## Result
- Observed current harm: Ideas dirty editor and dirty preview at 320px shift the workspace surface left (`workspace.left = -97`) while document overflow remains false. Toolbar action metrics pass, but screenshots show the route surface and controls clipped from the left.
- Recent Memory edit fix survives the 320px floor and remains usable.
- Kanban detail/edit and Decisions resolver findings are modal/background geometry artifacts or acceptable constrained flows; primary actions remain reachable.

## Follow-up
- #1764 fixes the Ideas dirty-mode horizontal shift.