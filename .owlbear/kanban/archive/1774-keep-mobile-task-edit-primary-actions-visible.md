---
id: 1774
title: Keep mobile task edit primary actions visible
status: archived
priority: medium
created: 2026-05-24T00:36:03.714982+02:00
updated: 2026-05-24T10:50:02.276529+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - mobile
  - task-detail
  - discussion
  - stress-note
parent: 1773
depends_on:
  - 1773
ac:
  - At 320px, opening task edit for a task with several tags and body content
    keeps Add tag, Save, and Cancel in an obviously reachable position or
    provides a clear sticky/action affordance.
  - The fix, if approved, does not reintroduce Add tag overlap or horizontal
    overflow.
  - Evidence distinguishes whether this is a task-content edge case or a general
    task edit layout issue before implementation.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
#1773 fresh sweep shows `320-kanban-task-edit` with Add tag visible near the bottom of the modal, but Save and Cancel below the 844px viewport (`top=815`, `bottom=871`). Screenshot: `.owlbear/scratch/1716-wide-cockpit/1773-320-kanban-task-edit.png`.

## Value Question
Editing a task should make the primary commit/cancel actions easy to find. This matters now because the tested task (#1773) is realistic for Cockpit work: several tags plus a moderate body.

## Current Interpretation
Reclassified after #1779: observed stress evidence below the 1024px Cockpit support floor, not current product harm. No implementation is approved from this task.

## Decision
Closed as a stress note. Future sweeps may still catch catastrophic sub-1024 breakage, but mobile task edit action placement is not a product-quality target for the desktop-only Cockpit.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1773-evidence-interaction-sweep-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-evidence-interaction-sweep-metrics.json`
- `.owlbear/scratch/1716-wide-cockpit/1773-320-kanban-task-edit.png`