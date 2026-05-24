---
id: 1759
title: Fix Ideas mobile preview toolbar clipping
status: archived
priority: important
created: 2026-05-23T16:16:27+0200
updated: 2026-05-24T10:50:02.080797+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - mobile
  - visual-proof
parent: 1758
depends_on:
  - 1758
ac:
  - On mobile, the Ideas dirty preview toolbar shows the unsaved badge, Edit
    action, and Save action without clipping.
  - Preview and editor toolbars remain reachable and readable at mobile width.
  - Desktop Ideas toolbar density and intent remain unchanged.
  - Screenshot and geometry metrics prove the dirty preview toolbar fits after
    the fix.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observed Issue
#1758 captured a current mobile Ideas problem: the dirty preview toolbar clips the right side of the `Save` action at the route surface edge.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1758-mobile-ideas-dirty-preview.png`
- `.owlbear/scratch/1716-wide-cockpit/1758-mobile-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1758-post-memory-filter-sweep-metrics.json`

## Value
Ideas is the user's notebook surface. When the save action is partially hidden in preview mode, the route communicates that edits may not be safely recoverable even though the underlying save behavior exists.

## Implementation
- Added an explicit `ideas-editor-toolbar` test hook for proof geometry.
- Let the Ideas toolbar use mobile-first left alignment with reduced mobile horizontal padding.
- Constrained the toolbar action group to the available mobile width so actions wrap inside the editor shell instead of being clipped.
- Preserved the desktop action row with `sm:w-auto sm:justify-end`.

## Validation
- `npm test -- --run $(find src/__tests__ -maxdepth 1 -name '*Ideas*' -print | sort)` — passed, 5 files and 143 tests.
- `npx eslint src/pages/IdeasPage.tsx` — passed.
- `npm run build` — passed, with the existing large chunk warning.

## Visual Proof
- `.owlbear/scratch/1716-wide-cockpit/1759-mobile-ideas-dirty-preview.png` shows `Unsaved changes`, `Edit`, and `Save` fully visible in preview mode.
- `.owlbear/scratch/1716-wide-cockpit/1759-mobile-ideas-dirty-editor.png` shows mobile editor actions wrapping without clipping.
- `.owlbear/scratch/1716-wide-cockpit/1759-desktop-ideas-dirty-preview.png` confirms the desktop toolbar remains dense and right-aligned.
- `.owlbear/scratch/1716-wide-cockpit/1759-ideas-toolbar-proof-metrics.json` reports no document overflow, no console messages, no request failures, and all toolbar actions inside both the toolbar and editor shell.