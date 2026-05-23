---
id: 1753
title: Keep mobile Kanban active lane visible
status: done
priority: important
created: 2026-05-23T11:49:57+0200
updated: 2026-05-23T11:54:02+0200
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - responsive
  - kanban
parent:
depends_on: [1752]
ac:
  - Use the #1752 mobile Kanban screenshot and metrics as current evidence.
  - On a 390x844 mobile viewport, the first non-empty/active Kanban lane is fully visible after board auto-alignment.
  - Preserve the existing one-leading-context-column behavior on wider strips when the active lane still fits.
  - Preserve horizontal scroll ownership inside the Kanban strip and avoid document-level overflow.
  - Add or update focused tests for the responsive auto-alignment decision.
  - Capture after-fix screenshot or metrics evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## User Feedback Context
The #1752 mobile sweep shows the Kanban route opening on a mostly empty Todo column while the In Progress lane containing the current task is clipped to a narrow sliver.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1752-mobile-kanban-rest.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1752-mobile-postfix-sweep-metrics.json`.
- Key geometry: the Kanban strip has `clientWidth: 356` and `scrollWidth: 1840`; Todo is fully visible while the In Progress task card begins at `left: 282` and extends to `right: 512`, outside the 390px viewport.

## Evaluation Notes
- Classification: observed current mobile usability issue.
- Current harm: moderate. The board technically scrolls, but the primary route opens on an empty lane and hides the active work lane.
- Product value: high. Kanban is the default Cockpit surface, and active work should be immediately legible on mobile.

## Implementation
- Updated Kanban initial auto-alignment to project whether the one-column context alignment still keeps the first non-empty lane fully visible.
- Preserved the context-column behavior when it fits; on narrow mobile strips, alignment now uses the first non-empty lane itself.
- Added a focused regression test for the narrow mobile decision while keeping the existing wide/context behavior test.

## Evidence After Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1753-mobile-kanban-active-lane.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1753-mobile-kanban-active-lane-metrics.json`.
- Browser proof on 390x844: `firstNonEmptyColumnWithinStrip: true`, `firstActiveCardWithinStrip: true`, `firstActiveCardWithinViewport: true`, `horizontalOverflow: false`, `verticalDocumentOverflow: false`, `consoleMessages: 0`.
- `npx vitest run src/__tests__/KanbanBoard.test.tsx --reporter=dot` passed: 41 tests.
- `npx eslint src/KanbanBoard.tsx src/__tests__/KanbanBoard.test.tsx` passed.
- `npm run build` passed; Vite repeated the existing chunk-size warning.
