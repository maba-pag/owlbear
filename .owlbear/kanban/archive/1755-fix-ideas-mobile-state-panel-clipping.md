---
id: 1755
title: Fix Ideas mobile state panel clipping
status: archived
priority: important
created: 2026-05-23T15:36:05+0200
updated: 2026-05-24T10:50:02.028059+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - mobile
  - visual-proof
parent: 1754
depends_on:
  - 1754
ac:
  - On mobile, the Ideas notebook/status panel content fits inside the visible
    workspace without clipped right-side values.
  - The Ideas editor and preview remain bounded with no document-level
    horizontal or vertical overflow.
  - Desktop Ideas layout remains a two-column work surface with the state panel
    as a sidebar.
  - Screenshot and geometry metrics prove the mobile panel, writing metrics, and
    edit controls fit after the fix.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observed Issue
#1754 captured a current mobile Ideas problem: the Notebook side panel is clipped horizontally inside the bounded workspace. The document itself does not report horizontal overflow, so the issue is local layout clipping rather than page-level scrolling.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1754-mobile-ideas.png`
- `.owlbear/scratch/1716-wide-cockpit/1754-mobile-ideas-edit-dirty.png`
- `.owlbear/scratch/1716-wide-cockpit/1754-current-state-sweep-metrics.json`

## Value
The Ideas tab is a writing notebook. On mobile, clipped status and metric values make the tab feel broken and reduce trust in saved/dirty state feedback. This hurts current usability, not just a theoretical future case.

## Resolution
- Kept the desktop Ideas sidebar behavior intact.
- Made the Ideas state panel width-safe with `min-w-0`/`overflow-hidden` and constrained notebook/metric rows.
- Adjusted mobile value alignment so status and metric values no longer sit flush against the clipped edge; desktop keeps right-aligned sidebar values.

## Validation
- `npm test -- --run src/__tests__/IdeasPage.test.tsx src/__tests__/IdeasPage_1662.test.tsx src/__tests__/IdeasPage_1663.test.tsx src/__tests__/IdeasPage_1664.test.tsx src/__tests__/IdeasPage_1665.test.tsx` — 143 tests passed.
- `npx eslint src/pages/IdeasPage.tsx` — passed.
- `npm run build` — passed; existing bundle-size warning only.

## Visual Proof
- `.owlbear/scratch/1716-wide-cockpit/1755-mobile-ideas-preview.png`
- `.owlbear/scratch/1716-wide-cockpit/1755-mobile-ideas-edit.png`
- `.owlbear/scratch/1716-wide-cockpit/1755-desktop-ideas-preview.png`
- `.owlbear/scratch/1716-wide-cockpit/1755-desktop-ideas-edit.png`
- `.owlbear/scratch/1716-wide-cockpit/1755-mobile-ideas-state-panel-clip-preview.png`
- `.owlbear/scratch/1716-wide-cockpit/1755-mobile-ideas-state-panel-clip-edit.png`

## Metrics
- `.owlbear/scratch/1716-wide-cockpit/1755-ideas-mobile-proof-metrics.json`: mobile/desktop preview and edit states report no document horizontal overflow, no vertical overflow, no clipped panel descendants, no console messages, and no request failures.
- `.owlbear/scratch/1716-wide-cockpit/1755-ideas-panel-clip-proof-metrics.json`: mobile panel `panelScrollFits=true` and `allRowsFit=true` in preview and edit modes.
