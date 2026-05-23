---
id: 1767
title: Cockpit post Ideas icon responsive sweep
status: done
priority: important
created: 2026-05-23T17:13:37.339322+02:00
updated: 2026-05-23T17:15:14+0200
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-proof
  - mobile
  - sweep
parent:
depends_on:
  - 1766
ac:
  - Capture Ideas dirty editor and dirty preview states at 320px, 390px, and 
    desktop after the PDS button icon fix.
  - Confirm Preview/Edit and Save controls render icon plus label without 
    clipping in each captured state.
  - 'Confirm the #1764 canvas-shift fix still holds in the affected Ideas states.'
  - Classify any remaining screenshot issue as observed current harm, plan risk,
    or acceptable constrained behavior before creating a follow-up fix task.
  - Record screenshot and metric evidence under 
    `.owlbear/scratch/1716-wide-cockpit/`.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Purpose
Verify the Ideas toolbar after #1766 across the responsive range most likely to expose icon/label clipping or the earlier canvas shift.

## Evaluation Frame
- Screenshots decide visual quality.
- Geometry must cover viewport bounds, control reachability, and canvas root horizontal scroll.
- Create a follow-up fix only for observed current harm.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1767-ideas-icon-responsive-sweep-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1767-ideas-icon-responsive-sweep-metrics.json`
- `.owlbear/scratch/1716-wide-cockpit/1767-320-dirty-editor.png`
- `.owlbear/scratch/1716-wide-cockpit/1767-320-dirty-preview.png`
- `.owlbear/scratch/1716-wide-cockpit/1767-390-dirty-editor.png`
- `.owlbear/scratch/1716-wide-cockpit/1767-390-dirty-preview.png`
- `.owlbear/scratch/1716-wide-cockpit/1767-1440-dirty-editor.png`
- `.owlbear/scratch/1716-wide-cockpit/1767-1440-dirty-preview.png`

## Result
- No metric issues across six Ideas dirty editor/preview states at 320px, 390px, and 1440px.
- Preview/Edit and Save controls render with PDS icons plus labels and remain reachable.
- The #1764 canvas-shift fix still holds in the affected Ideas states: canvas root scroll remains reset and the route stays inside the viewport.
- Screenshot review found no observed current harm in this focused responsive pass.