---
id: 1741
title: Keep task detail edit actions visible
status: done
priority: needed
created: 2026-05-23T10:21:47+0200
updated: 2026-05-23T10:28:21+0200
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - edit-mode
parent:
depends_on: [1740]
ac:
  - Use the #1740 edit-mode sweep as current evidence.
  - Keep Save, Cancel, and dirty/save feedback reachable in the initial edit-mode viewport.
  - Preserve the viewport-bounded task detail modal and vertical-only internal scrolling.
  - Preserve existing save, cancel, validation, and unsaved-change behavior.
  - Add or update focused tests for the visible edit-action contract where practical.
  - Capture after-fix screenshot or metrics evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## User Feedback Context
The #1740 edit-mode sweep shows the modal and scroll surface are bounded, but the edit form's primary actions are below the first visible modal viewport. Users can edit fields immediately but must scroll far down to save, cancel, or see the dirty indicator.

## Evidence Before Fix
- Screenshots: `.owlbear/scratch/1716-wide-cockpit/1740-task-detail-edit.png`, `.owlbear/scratch/1716-wide-cockpit/1740-task-detail-dirty.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1740-task-detail-edit-sweep-metrics.json` reports content viewport `top: 230`, `bottom: 950`, while `saveButton.top: 1451`, `cancelEditButton.top: 1451`, and dirty indicator `top: 1467` in dirty state.

## Evaluation Notes
- Classification: observed current interaction usability issue.
- Current harm: core edit completion controls are reachable only after scrolling through a long form.
- Product value: task editing is a primary Cockpit workflow; persistent action visibility makes the bounded modal feel intentional and efficient.

## Implementation
- Moved the existing Save, Cancel, dirty, saved, and validation feedback row into a sticky `task-detail-edit-actions` toolbar inside the task detail edit form.
- Threaded edit-mode state from `TaskFieldsEditor` through `DetailTab` to `Shell` so the display-mode bottom scroll cue is suppressed while the sticky edit toolbar owns the bottom of the modal.
- Preserved existing save, cancel, dirty, validation, and unsaved-change behavior by reusing the existing controls and handlers.
- Added focused tests for the sticky edit action bar and for hiding the task-detail scroll cue while edit mode is active.

## Evidence After Fix
- Screenshots:
  - `.owlbear/scratch/1716-wide-cockpit/1741-task-detail-sticky-edit-actions.png`
  - `.owlbear/scratch/1716-wide-cockpit/1741-task-detail-sticky-dirty.png`
  - `.owlbear/scratch/1716-wide-cockpit/1741-task-detail-sticky-unsaved-dialog.png`
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1741-task-detail-sticky-edit-actions-metrics.json` reports task detail window `bottom: 950`, content `overflowX: hidden` / `overflowY: auto`, action bar `position: sticky`, Save `top: 854` / `bottom: 910`, Cancel `top: 854` / `bottom: 910`, and dirty indicator `top: 870` / `bottom: 894`.
- Metrics flags: `horizontalOverflow: false`, `verticalDocumentOverflow: false`, `taskDetailBottomWithinViewport: true`, `contentVerticalOnly: true`, `actionBarVisibleInContentViewport: true`, `saveButtonVisibleInContentViewport: true`, `cancelButtonVisibleInContentViewport: true`, `dirtyIndicatorVisibleInContentViewport: true`, and no console messages.
- Validation: `npx vitest run src/__tests__/DetailTab.test.tsx src/__tests__/Shell.callbacks.test.tsx src/__tests__/Shell.test.tsx --reporter=verbose` passed; `npx eslint src/components/TaskFieldsEditor.tsx src/components/DetailTab.tsx src/Shell.tsx src/__tests__/DetailTab.test.tsx src/__tests__/Shell.callbacks.test.tsx` passed; `npm run build` passed with the existing Vite chunk-size warning.
