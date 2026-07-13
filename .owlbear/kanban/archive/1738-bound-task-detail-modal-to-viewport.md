---
id: 1738
title: Bound task detail modal to viewport
status: archived
priority: medium
created: 2026-05-23T04:58:00+0200
updated: 2026-05-24T10:50:01.788019+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - layout
parent:
depends_on: []
ac:
  - Reproduce the task detail window extending below the desktop viewport in the
  - Keep task detail content fully reachable inside the modal without expanding
    the document.
  - Preserve existing task detail display/edit actions and unsaved-change
    behavior.
  - Add or update focused tests for the modal viewport bounds contract where
    practical.
  - Capture after-fix screenshot or metrics evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## User Feedback Context
The interaction sweep shows task detail is visually clipped at the bottom of a 1440x1000 desktop viewport. Metadata starts at the bottom edge, so users cannot comfortably inspect task details without the modal feeling cut off.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1737-task-detail.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1737-interaction-sweep-metrics.json` reports task detail window `top: 130`, `height: 880`, and `bottom: 1010` at a 1000px viewport.

## Evaluation Notes
- Classification: observed current interaction usability issue.
- Current harm: core task detail content is clipped by the viewport.
- Product value: task detail inspection/edit is a primary Cockpit workflow; the modal should feel contained and fully reachable.

## Implementation
- Changed the task detail modal window from `max-h-[min(88vh,900px)]` to `max-h-[min(84vh,820px)]`, matching the resolver modal's proven viewport envelope while leaving the existing internal content scroll region intact.
- Added a focused Shell callback test that asserts the modal window has bounded max-height/overflow and the task detail content region keeps `min-h-0 overflow-y-auto`.

## Evidence After Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1738-task-detail-bounded-after.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1738-task-detail-bounded-after-metrics.json` opened task #1738 at a 1440x1000 viewport and reports task detail window `top: 130`, `height: 820`, `bottom: 950`.
- Metrics flags: `horizontalOverflow: false`, `verticalDocumentOverflow: false`, `taskDetailBottomWithinViewport: true`, `taskDetailContentScrollsInternally: true`, and no console messages.
- Validation: `npx vitest run src/__tests__/Shell.callbacks.test.tsx src/__tests__/Shell.test.tsx --reporter=verbose` passed 43 tests; `npx eslint src/Shell.tsx src/__tests__/Shell.callbacks.test.tsx` passed; `npm run build` passed with the existing Vite chunk-size warning.
