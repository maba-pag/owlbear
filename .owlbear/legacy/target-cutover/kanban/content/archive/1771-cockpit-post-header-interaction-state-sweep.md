---
id: 1771
title: Cockpit post header interaction-state sweep
status: archived
priority: medium
created: 2026-05-23T23:58:03+02:00
updated: 2026-05-24T10:50:02.248997+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - interaction-states
  - responsive
parent:
depends_on:
  - 1770
ac:
  - Current Cockpit screenshots cover representative opened panels, dialogs,
    dirty/edit states, and global header menus after the Canvas header fix.
  - The sweep checks 320px, 390px, and desktop widths where practical for
    viewport clipping, horizontal shift, hidden actions, and overlapping shell
    chrome.
  - Screenshots are reviewed directly, not only by geometry metrics.
  - Any screenshot-confirmed current harm is captured as a focused follow-up
    task rather than folded into the sweep.
  - The sweep records proof paths, findings, and next action.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Purpose
Run a screenshot-led interaction-state sweep after #1769/#1770 proved the global header rest states are clean.

## Scope
Cover states that are more likely to expose clipping or affordance problems than route rest screens: task detail/edit, health and theme popovers, decisions resolver when available, memory edit when available, and Ideas dirty editor/preview.

## Findings
Initial screenshot review found one current task-detail edit issue on mobile: the Add tag row and Save/Cancel controls were cramped and visually collided in the task detail modal. That was split into #1772 and fixed before closing this sweep.

Post-fix sweep captured 24 interaction screenshots across 320px, 390px, and desktop widths:
- Header health popover and theme menu remain visible and reachable at all widths.
- Kanban task detail and task edit states are usable after #1772; Save/Cancel and Add tag are distinct and reachable at 320px and 390px.
- Decisions resolver, memory edit, and Ideas dirty editor/preview states remain usable at the captured widths.
- No console errors, request failures, horizontal overflow, window horizontal shift, or Canvas root scroll regression were recorded.
- Metric noise remains for whole edit-form containers whose full scroll height extends below the viewport (`task-detail-edit-form` and `memory-edit-form`). Screenshot review confirms the visible controls are reachable and this is expected for scrollable long forms, not current harm.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1771-interaction-state-sweep-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1771-interaction-state-sweep-metrics.json`
- `.owlbear/scratch/1716-wide-cockpit/1771-320-kanban-task-edit.png`
- `.owlbear/scratch/1716-wide-cockpit/1771-390-kanban-task-edit.png`
- `.owlbear/scratch/1716-wide-cockpit/1771-1440-kanban-task-edit.png`
- `.owlbear/scratch/1716-wide-cockpit/1772-task-edit-modal-proof-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1772-task-edit-modal-proof-metrics.json`