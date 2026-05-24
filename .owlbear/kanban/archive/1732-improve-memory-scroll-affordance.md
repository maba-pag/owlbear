---
id: 1732
title: Improve Memory scroll affordance
status: archived
priority: important
created: 2026-05-23T03:47:09+0200
updated: 2026-05-24T10:50:01.702945+02:00
tags:
  - cockpit
  - memory
  - layout
  - ux-feedback
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
type: bug
assignee: copilot
---

## Problem
After bounding the Cockpit workspace, the Memory list correctly scrolls internally, but the list has no clear visual cue that many more entries continue below the fold. Metrics also show the Memory list has `overflow-x: auto`, even though horizontal scrolling is not intended for entry rows.

## Acceptance Criteria
- The Memory entry list keeps vertical internal scrolling for long result sets.
- The Memory entry list does not expose unnecessary horizontal scrolling.
- The bottom of the Memory list communicates continuation or depth without adding instructional text.
- Existing Memory filtering and row behavior remain unchanged.
- Add or update focused tests for the list scroll contract.
- Capture after-fix screenshot or metrics evidence.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1731-memory-desktop.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1731-desktop-sweep-metrics.json` shows Memory list `overflowX: auto`, `overflowY: auto`, `scrollHeight: 8053`, and `clientHeight: 678`.

## Evidence After Fix
- Memory list now sits inside a bounded scroll shell, uses `overflow-x: hidden` and `overflow-y: auto`, and shows a non-interactive bottom fade while more entries continue below the fold.
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1732-memory-scroll-affordance-after.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1732-memory-scroll-affordance-after-metrics.json` reports document height 1000px, list `overflowX: hidden`, list `overflowY: auto`, `scrollHeight: 8085`, `clientHeight: 678`, and cue present with `pointer-events: none`.
- Focused Vitest passed: `src/__tests__/MemoryTab_1671.test.tsx`, 55 tests. Existing verbose PDS option warnings appeared in the log.
- ESLint passed for `src/pages/MemoryTab.tsx` and `src/__tests__/MemoryTab_1671.test.tsx`.
- `npm run build` passed with the existing Vite chunk-size warning.
