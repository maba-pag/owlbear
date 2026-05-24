---
id: 1739
title: Add task detail scroll affordance
status: archived
priority: important
created: 2026-05-23T10:10:47+0200
updated: 2026-05-24T10:50:01.803353+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - layout
parent:
depends_on:
  - 1738
ac:
  - Use the
  - Keep the modal viewport-bounded while making additional scrollable content
    discoverable.
  - Avoid horizontal overflow in the task detail content region.
  - Preserve existing display/edit actions and unsaved-change behavior.
  - Add or update focused tests for the scroll affordance contract where
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
After #1738, the task detail modal is contained in the viewport, but the task detail content region now cuts directly at the modal bottom. When more task metadata or acceptance criteria continue below the fold, the UI gives little visual hint that the panel itself scrolls.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1738-task-detail-bounded-after.png` shows the acceptance criteria list clipped by the lower edge of the scroll region.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1738-task-detail-bounded-after-metrics.json` reports `taskDetailContent` with `clientHeight: 720`, `scrollHeight: 1146`, and `overflowY: auto`.

## Evaluation Notes
- Classification: observed current interaction usability issue.
- Current harm: users can scroll, but the continuation is visually subtle and can look like content is cut off.
- Product value: task detail is a primary Cockpit workflow; a restrained scroll cue helps the bounded modal feel intentional and complete.

## Implementation
- Added a `task-detail-scroll-shell` inside the bounded modal and made the task detail body an inset, vertical-only scroll viewport.
- Added bottom padding plus a non-interactive bottom fade cue that appears only while more modal content remains below.
- Kept the #1738 modal viewport budget by giving the task detail window a fixed `h-[min(84vh,820px)]` and matching `max-h-[min(84vh,820px)]`.
- Added focused Shell callback tests for the bounded scroll-shell contract and cue visibility at top vs. bottom scroll positions.

## Evidence After Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1739-task-detail-scroll-cue-after.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1739-task-detail-scroll-cue-after-metrics.json` opened task #1738 at a 1440x1000 viewport and reports task detail window `top: 130`, `height: 820`, `bottom: 950`; content viewport `height: 720`, `scrollHeight: 1611`, `overflowX: hidden`, `overflowY: auto`; cue `top: 910`, `bottom: 950`.
- Metrics flags: `horizontalOverflow: false`, `verticalDocumentOverflow: false`, `taskDetailBottomWithinViewport: true`, `taskDetailContentHasMoreBelow: true`, `taskDetailCueVisible: true`, `taskDetailContentVerticalOnly: true`, and no console messages.
- Validation: `npx vitest run src/__tests__/Shell.callbacks.test.tsx src/__tests__/Shell.test.tsx --reporter=verbose` passed 44 tests; `npx eslint src/Shell.tsx src/__tests__/Shell.callbacks.test.tsx` passed; `npm run build` passed with the existing Vite chunk-size warning.
