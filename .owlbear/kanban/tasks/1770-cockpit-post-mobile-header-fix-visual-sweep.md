---
id: 1770
title: Cockpit post mobile header fix visual sweep
status: done
priority: important
created: 2026-05-23T17:59:39+02:00
updated: 2026-05-23T18:02:41+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - responsive
parent:
depends_on:
  - 1769
ac:
  - Current Cockpit screenshots cover mobile and desktop states most likely to regress after the Canvas header clipping fix.
  - The sweep checks no horizontal document overflow, no hidden or clipped global header controls, and no obvious overlap between shell chrome and workspace content.
  - Screenshots are reviewed directly, not only by geometry metrics.
  - Any screenshot-confirmed current harm is captured as a focused follow-up task rather than folded into the sweep.
  - The sweep records proof paths, findings, and next action.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Purpose
Run a focused current-state visual sweep after #1769 changed PDS Canvas root overflow from clipped to visible for the mobile header.

## Scope
Cover the global shell header and representative workspace surfaces at 320px, 390px, and desktop widths. Prioritize routes and states where clipping, horizontal shift, or hidden controls would be user-visible.

## Findings
The 12-screenshot sweep covered Kanban, Decisions, Memory, and Ideas at 320px, 390px, and 1440px after the #1769 Canvas root overflow change. Geometry metrics reported no horizontal document overflow, no Canvas root scrollLeft regression, no hidden/clipped global header controls, no header/status overlap with the centered identity, and no console errors or failed requests. Direct screenshot review also found no screenshot-confirmed current harm from the header fix.

## Proof
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1770-post-header-fix-sweep-metrics.json`
- Contact sheet: `.owlbear/scratch/1716-wide-cockpit/1770-post-header-fix-sweep-contact-sheet.png`
- Screenshots: `.owlbear/scratch/1716-wide-cockpit/1770-320-kanban-rest.png`, `.owlbear/scratch/1716-wide-cockpit/1770-320-decisions-rest.png`, `.owlbear/scratch/1716-wide-cockpit/1770-320-memory-rest.png`, `.owlbear/scratch/1716-wide-cockpit/1770-320-ideas-rest.png`, `.owlbear/scratch/1716-wide-cockpit/1770-390-kanban-rest.png`, `.owlbear/scratch/1716-wide-cockpit/1770-390-decisions-rest.png`, `.owlbear/scratch/1716-wide-cockpit/1770-390-memory-rest.png`, `.owlbear/scratch/1716-wide-cockpit/1770-390-ideas-rest.png`, `.owlbear/scratch/1716-wide-cockpit/1770-1440-kanban-rest.png`, `.owlbear/scratch/1716-wide-cockpit/1770-1440-decisions-rest.png`, `.owlbear/scratch/1716-wide-cockpit/1770-1440-memory-rest.png`, `.owlbear/scratch/1716-wide-cockpit/1770-1440-ideas-rest.png`

## Next Action
No focused follow-up task from this pass.