---
id: 1757
title: Fix Memory mobile filter control clipping
status: done
priority: important
created: 2026-05-23T15:54:30+0200
updated: 2026-05-23T16:09:07+0200
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - mobile
  - visual-proof
parent: 1756
depends_on: [1756]
ac:
  - On mobile, Memory filter controls fit inside the visible workspace without clipped right edges or partially hidden affordance icons.
  - The Memory route remains document-bounded with no horizontal or vertical page overflow.
  - Desktop Memory layout remains dense and unchanged in intent.
  - Screenshot and geometry metrics prove the filter panel controls fit after the fix.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observed Issue
#1756 captured a current mobile Memory problem: PDS filter controls in the Memory filter panel are clipped at the right edge. The page itself does not horizontally overflow, so the issue is local layout clipping inside the route surface.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1756-mobile-memory.png`
- `.owlbear/scratch/1716-wide-cockpit/1756-mobile-memory-edit.png`
- `.owlbear/scratch/1716-wide-cockpit/1756-post-ideas-sweep-metrics.json`

## Value
Memory is a scanning and curation surface. If the filter controls look cut off on mobile, the user cannot trust the filter affordances and the route reads as unfinished even when the data is valid.

## Implementation
- Reduced the Memory route mobile horizontal gutters while preserving the original tablet/desktop spacing.
- Reduced the mobile-only filter panel horizontal padding so PDS controls have more usable width on 390px viewports.
- Set the PDS filter hosts to explicit full-width blocks with `w-full min-w-0 max-w-full`.

## Validation
- `npm test -- --run $(find src/__tests__ -maxdepth 1 -name '*Memory*' -print | sort)` — passed, 2 files and 135 tests.
- `npx eslint src/pages/MemoryTab.tsx` — passed.
- `npm run build` — passed, with the existing large chunk warning.

## Visual Proof
- `.owlbear/scratch/1716-wide-cockpit/1757-mobile-memory-filters.png` shows the Memory filter panel fitting on mobile without clipped right-edge affordances.
- `.owlbear/scratch/1716-wide-cockpit/1757-mobile-memory-filter-panel-clip.png` captures the fixed panel crop.
- `.owlbear/scratch/1716-wide-cockpit/1757-desktop-memory-filters.png` confirms the dense desktop filter layout remains intact.
- `.owlbear/scratch/1716-wide-cockpit/1757-memory-filter-proof-metrics.json` reports mobile document overflow false, desktop document overflow false, all controls inside the panel, and all controls scroll-fit.
- `.owlbear/scratch/1716-wide-cockpit/1757-memory-filter-panel-clip-metrics.json` reports a 340px mobile filter panel with 330px-wide controls after the fix.
