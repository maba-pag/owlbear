---
id: 1791
title: Align Kanban filters with trigger and clear action
status: archived
priority: important
created: 2026-05-24T01:57:03.822491+02:00
updated: 2026-05-24T10:50:02.511279+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - filters
  - discussion
parent: 1773
depends_on: []
ac:
  - Opening Kanban filters visually relates the filter UI to the right-side
    Filter trigger.
  - When filters are active, users can clear them without reopening the filter
    popup/panel.
  - The active-filter indicator remains readable at supported desktop widths.
  - No implementation begins until the user approves this task.
  - Kanban filter UI uses an anchored popover/menu pattern rather than a
    left-aligned full-width panel, unless proof shows the popover cannot hold
    the controls well.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User feedback on Kanban filters:
1. When opened, the filter popup/panel is left-aligned even though the Filter button and current-filter indicator are on the right side of the board.
2. The active-filter bar should probably include a Clear filters button so filters can be reset easily even when the filter popup is closed.

## Current Interpretation
Observed workflow polish issue. Filter controls and active filter feedback are spatially disconnected, and clearing filters may be less discoverable than setting them.

## Value
Filters are a repeated board workflow. Users should understand which controls belong together and be able to recover quickly from a filtered board.

## Discussion Questions
- Should the filter UI be a right-aligned popover under the Filter button, or a full-width panel with stronger right-side anchoring?
- Should Clear filters appear only when filters are active?
- Should active filter chips live in the header row, inside the panel, or both?

[[2026-05-24T03:13:48+02:00]]
## Decision
User prefers trying a popover pattern for Kanban filters, similar in interaction feel to the workspace status/health menu: anchored to the Filter trigger, dismissible, and spatially connected to the right-side header controls. Active filters should still have an accessible Clear filters action outside the popover.

## Implementation Proof
- Changed the Kanban filter panel from a left-aligned board panel to a right-anchored popover under the header action cluster.
- Added a header-level `Clear filters` action that appears while filters are active and works even after the popover is closed.
- Kept the existing in-popover `Clear all` action and PDS controls intact.

## Verification
- `npm test -- --run src/__tests__/KanbanBoard.filter-e2e.test.tsx src/__tests__/FilterPanel.pds-controls.test.tsx` — 28 passed.
- `npm test -- --run src/__tests__/KanbanBoard.filter-integration.test.tsx src/__tests__/FilterAccessibility.test.tsx src/__tests__/FilterAccessibilityPanel.test.tsx src/__tests__/FilterPanel.test.tsx` — 73 passed.
- `npx eslint src/KanbanBoard.tsx src/__tests__/KanbanBoard.filter-e2e.test.tsx src/__tests__/FilterPanel.pds-controls.test.tsx` — passed.
- `npm run build` — passed with the known Vite chunk-size warning.
- `git diff --check` for the #1791 files — passed.

## Visual Proof
- `.owlbear/scratch/1716-wide-cockpit/1791-kanban-filter-popover-1024.png`
- `.owlbear/scratch/1716-wide-cockpit/1791-kanban-filter-popover-1440.png`

## Screenshot Metrics
- 1024 viewport: panel left 248, right 968, width 720; result count `1 / 3 tasks`; active chip `Priority: Critical`.
- 1440 viewport: panel left 664, right 1384, width 720; result count `1 / 3 tasks`; active chip `Priority: Critical`.

[[2026-05-24T05:02:21+02:00]]
Implemented the approved Kanban filter popover polish: right-anchored filter panel, active-state Clear filters action outside the popover, focused behavioral/source tests, lint/build, and screenshots at 1024 and 1440.
