---
id: 1761
title: Fix Memory mobile edit left edge clipping
status: archived
priority: important
created: 2026-05-23T16:27:11+0200
updated: 2026-05-24T10:50:02.109114+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - mobile
  - visual-proof
parent: 1760
depends_on:
  - 1760
ac:
  - Opening Memory edit mode on mobile does not shift the workspace or route
    surface left of the viewport.
  - Memory edit actions remain visible and reachable after edit mode opens.
  - The Memory filter panel and edit form remain horizontally bounded with no
    document-level overflow.
  - Desktop Memory edit behavior remains unchanged in intent.
  - Screenshot and geometry metrics prove the mobile edit state fits after the
    fix.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observed Issue
#1760 confirmed a repeat mobile Memory issue: opening edit mode shifts the workspace left, visibly clipping the route surface. The document does not horizontally overflow, so the defect is local scroll-position/layout behavior during the edit transition.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1760-mobile-memory-edit.png`
- `.owlbear/scratch/1716-wide-cockpit/1760-post-ideas-toolbar-sweep-metrics.json`

## Suspected Cause
`MemoryTab` calls `memoryEditActionsRef.current?.scrollIntoView({ block: 'start', inline: 'nearest' })` after edit mode opens. On mobile, that can adjust horizontal positioning while trying to reveal the sticky edit action row, shifting the workspace left even though the page remains document-bounded.

## Value
Memory edit is a core curation workflow. If the route clips sideways as soon as editing begins, the surface feels unstable and the user loses trust in the edit controls.

## Implementation
- Replaced the edit-mode `scrollIntoView({ block: 'start', inline: 'nearest' })` call with vertical-only scrolling on the Memory list container.
- Reset the Memory list horizontal scroll position to `0` whenever edit mode opens.
- Added a jsdom-safe fallback for environments without native `scrollTo`.
- Updated the edit-mode test to prove the vertical-only list-scroll contract and forbid `scrollIntoView`.

## Validation
- `npm test -- --run src/__tests__/MemoryTab_1671.test.tsx src/__tests__/MemoryTab_1672.test.tsx --reporter=dot` — passed, 2 files and 135 tests.
- `npx eslint src/pages/MemoryTab.tsx src/__tests__/MemoryTab_1672.test.tsx` — passed.
- `npm run build` — passed, with the existing large chunk warning.

## Visual Proof
- `.owlbear/scratch/1716-wide-cockpit/1761-mobile-memory-edit.png` shows Memory edit mode no longer clipped at the left edge.
- `.owlbear/scratch/1716-wide-cockpit/1761-desktop-memory-edit.png` confirms desktop Memory edit remains dense and usable.
- `.owlbear/scratch/1716-wide-cockpit/1761-memory-edit-proof-metrics.json` reports mobile `workspace.left = 17`, `memoryTab.left = 17`, no document overflow, `memoryList.scrollLeft = 0`, visible edit actions inside the list shell, no console messages, and no request failures.