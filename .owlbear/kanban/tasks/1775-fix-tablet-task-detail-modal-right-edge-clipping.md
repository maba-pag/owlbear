---
id: 1775
title: Fix tablet task detail modal right-edge clipping
status: done
priority: important
created: 2026-05-24T00:36:19.235089+02:00
updated: 2026-05-24T00:51:53+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - tablet
  - task-detail
  - discussion
  - stress-note
parent: 1773
depends_on:
  - 1773
ac:
  - At 768px width, task detail and task edit modal surfaces stay inside the
    viewport horizontally.
  - Task edit fields and Add tag controls do not extend beyond the visible modal
    column.
  - Desktop and phone modal behavior remain intentional if this is approved for
    implementation.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
#1773 fresh sweep shows tablet-width task detail/edit modals extending past the right viewport: `768-kanban-task-detail` detail window right edge is 818 in a 768px viewport; `768-kanban-task-edit` form and Add tag also extend to x=805. Screenshots: `.owlbear/scratch/1716-wide-cockpit/1773-768-kanban-task-detail.png` and `.owlbear/scratch/1716-wide-cockpit/1773-768-kanban-task-edit.png`.

## Value Question
Tablet is a plausible Cockpit viewport, and clipped modals make the interface feel less controlled. The issue is about trust and reachability, not aesthetic preference only.

## Current Interpretation
Reclassified after #1779: observed stress evidence below the 1024px Cockpit support floor, not current product harm. No implementation is approved from this task.

## Decision
Closed as a stress note. The next task-detail modal judgement must use 1024px+ evidence.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1773-evidence-interaction-sweep-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-evidence-interaction-sweep-metrics.json`
- `.owlbear/scratch/1716-wide-cockpit/1773-768-kanban-task-detail.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-768-kanban-task-edit.png`