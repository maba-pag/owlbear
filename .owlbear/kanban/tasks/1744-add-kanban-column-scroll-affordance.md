---
id: 1744
title: Add Kanban column scroll affordance
status: done
priority: important
created: 2026-05-23T10:46:10+0200
updated: 2026-05-23T10:51:27+0200
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - layout
parent:
depends_on: [1743]
ac:
  - Use the #1743 Kanban screenshot and metrics as current evidence.
  - Show a subtle continuation affordance when a Kanban column has more vertical content below its visible body.
  - Hide the affordance when the column is scrolled to the bottom or has no vertical overflow.
  - Preserve the bounded board layout and horizontal column strip behavior.
  - Add or update focused tests for the column scroll-affordance contract where practical.
  - Capture after-fix screenshot or metrics evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## User Feedback Context
The #1743 desktop sweep shows the Done lane has more cards than the visible column body can show, with a card cut off at the bottom of the first viewport.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1743-kanban-desktop.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1743-current-tabs-metrics.json` reports the board remains bounded (`workspaceBottomWithinViewport: true`, no document overflow), while multiple Done-lane task card elements extend below the visible 1000px viewport inside the column scroll surface.

## Evaluation Notes
- Classification: observed current interaction usability issue.
- Current harm: the lane is technically scrollable, but the clipped card gives no explicit continuation signal comparable to the Memory and task-detail scroll affordances.
- Product value: Kanban is the primary Cockpit work surface, and long lanes need obvious continuation without adding visual noise to quiet/empty lanes.

## Implementation
- Added a `Column` overflow detector that tracks whether the column body has more vertical content below the current scroll position.
- Added a subtle bottom fade cue inside overflowing columns and hid it when the column reaches the bottom.
- Made column bodies explicitly vertical-only with `overflow-x-hidden overflow-y-auto`.
- Preserved the existing bounded board layout, horizontal column strip, quiet lane chrome, and task sorting behavior.
- Added focused tests for vertical-only column bodies, cue visibility while content continues, and cue removal at the bottom.

## Evidence After Fix
- Screenshots:
  - `.owlbear/scratch/1716-wide-cockpit/1744-kanban-column-cue.png`
  - `.owlbear/scratch/1716-wide-cockpit/1744-kanban-column-cue-bottom.png`
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1744-kanban-column-cue-metrics.json` reports the Done column visible inside the board, column body `overflowX: hidden` / `overflowY: auto`, cue `top: 927` / `bottom: 959` while more content remains, and `doneColumnScrollCue: null` after scrolling to the bottom.
- Metrics flags: `horizontalOverflow: false`, `verticalDocumentOverflow: false`, `doneColumnVisible: true`, `doneBodyVerticalOnly: true`, and `cueVisibleInDoneBody: true` before bottom scroll; after bottom scroll, `cueVisibleInDoneBody: false`.
- Validation: `npx vitest run src/__tests__/Column.test.tsx src/__tests__/KanbanBoard.test.tsx src/__tests__/BoardVisualDesign.test.tsx --reporter=verbose` passed; `npx eslint src/components/Column.tsx src/__tests__/Column.test.tsx` passed; `npm run build` passed with the existing Vite chunk-size warning.