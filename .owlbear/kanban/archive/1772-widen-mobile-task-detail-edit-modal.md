---
id: 1772
title: Widen mobile task detail edit modal
status: archived
priority: medium
created: 2026-05-24T00:03:04+02:00
updated: 2026-05-24T10:50:02.264711+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - mobile
  - visual-proof
  - task-detail
parent:
depends_on:
  - 1771
ac:
  - At 320px and 390px widths, the task detail edit modal gives editable fields
    enough horizontal room for tags, Add tag, Save, and Cancel controls to read
    as intentional.
  - The edit action bar remains reachable without visually burying the Add tag
    row or cramped tags area.
  - Desktop task detail modal width and scroll behavior remain unchanged in
    intent.
  - Focused screenshots and geometry metrics prove the fix with no console
    errors, failed requests, horizontal overflow, or Canvas root scroll
    regression.
  - The
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Purpose
Fix the screenshot-confirmed mobile task detail edit issue found in #1771: the task edit modal is too narrow on mobile, making tags, Add tag, and sticky Save/Cancel controls feel cramped and partially buried.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1771-interaction-state-sweep-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1771-320-kanban-task-edit.png`
- `.owlbear/scratch/1716-wide-cockpit/1771-390-kanban-task-edit.png`
- `.owlbear/scratch/1716-wide-cockpit/1772-task-edit-modal-proof-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1772-task-edit-modal-proof-metrics.json`
- `.owlbear/scratch/1716-wide-cockpit/1772-320-task-edit.png`
- `.owlbear/scratch/1716-wide-cockpit/1772-390-task-edit.png`
- `.owlbear/scratch/1716-wide-cockpit/1772-1440-task-edit.png`

## Finding
The task detail modal used the same `calc(100vw - 8rem)` width budget on mobile and desktop. On 320px mobile, that left the internal task edit form very narrow, causing tag chips and the Add tag row to collide visually with the sticky edit actions.

## Fix
The mobile modal now uses a wider mobile width budget and a viewport-safe height cap, while preserving the desktop width intent. The task detail editor now constrains single-column grids with `minmax(0,1fr)`, trims mobile-only card padding in the task details section, and keeps Save/Cancel in normal document flow on mobile so they cannot float over Add tag.

## Validation
- `npm test -- --run src/__tests__/Shell.callbacks.test.tsx src/__tests__/Shell.test.tsx src/__tests__/DetailTab.test.tsx`: passed, 107 passed and 1 skipped.
- `npx eslint src/Shell.tsx src/__tests__/Shell.callbacks.test.tsx src/components/TaskFieldsEditor.tsx src/components/DetailTab.tsx`: passed.
- `npm run build`: passed with the existing large-chunk warning.
- Focused #1772 proof passed with no issues at 320, 390, and 1440 widths: no horizontal overflow, no Canvas root scroll regression, no console messages, no failed requests, Add tag is not covered, and Save/Cancel remain inside the viewport.
- Post-fix #1771 interaction sweep was rerun and updated.