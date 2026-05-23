---
id: 1751
title: Keep mobile Memory edit actions visible
status: done
priority: important
created: 2026-05-23T11:29:42+0200
updated: 2026-05-23T11:41:46+0200
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - memory
  - responsive
  - edit-mode
parent:
depends_on: [1748]
ac:
  - Use the #1748 mobile Memory edit screenshot and metrics as current evidence.
  - Keep Memory edit Save and Cancel visible and reachable on a 390x844 mobile viewport after entering edit mode.
  - Avoid mutating memory data during the visual proof.
  - Preserve the bounded Memory workspace, list scroll shell, desktop sticky edit header behavior, and no document-level overflow.
  - Add or update focused tests for the Memory edit positioning/action visibility contract where practical.
  - Capture after-fix mobile screenshot or metrics evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## User Feedback Context
The #1748 mobile Memory edit capture shows the edit action header starting at the bottom of the visible list shell, with Save and Cancel barely/cut-off at the 844px viewport edge.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1748-mobile-memory-edit.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1748-mobile-interaction-metrics.json`.
- Key metrics: `memoryListShell.top: 567`, `memoryListShell.bottom: 811`, `memoryListShell.scrollHeight: 1278`; edit form starts at `top: 769`; `memoryEditActions.top: 770`, `bottom: 863`; `memoryEditSave.bottom: 854` on an 844px viewport.

## Evaluation Notes
- Classification: observed current mobile usability issue.
- Current harm: moderate. Edit actions exist and sticky behavior works after list movement, but starting edit leaves Save/Cancel partly outside the visible mobile viewport.
- Product value: high enough to fix because Memory edit is a primary mutation workflow and should be immediately controllable after entering edit mode.

## Implementation
- Added a Memory edit action-bar ref and, when edit mode starts, schedules a browser-frame scroll that aligns the sticky Save/Cancel header to the start of the Memory list scroll surface.
- Kept the existing bounded list shell and sticky edit-header layout intact; the fix only changes the initial scroll position after entering edit mode.
- Added a focused MemoryTab contract test proving edit mode requests the action bar alignment.

## Evidence After Fix
- First proof with `block: nearest` failed: Save/Cancel still landed below the 844px mobile viewport (`editSaveWithinViewport: false`, `editCancelWithinViewport: false`).
- Final screenshot: `.owlbear/scratch/1716-wide-cockpit/1751-memory-mobile-edit-fit.png`.
- Final metrics: `.owlbear/scratch/1716-wide-cockpit/1751-memory-mobile-edit-fit-metrics.json`.
- Final browser metrics on 390x844: `editSaveWithinViewport: true`, `editCancelWithinViewport: true`, `editButtonsWithinListShell: true`, `horizontalOverflow: false`, `verticalDocumentOverflow: false`, `consoleMessages: 0`.
- `npx vitest run src/__tests__/MemoryTab_1672.test.tsx --reporter=dot` passed: 80 tests.
- `npx eslint src/pages/MemoryTab.tsx src/__tests__/MemoryTab_1672.test.tsx` passed.
- `npm run build` passed; Vite repeated the existing chunk-size warning.
