---
id: 1801
title: Simplify Kanban filter summary counter
status: archived
priority: important
created: 2026-05-24T06:03:00+02:00
updated: 2026-05-24T10:50:02.640992+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - filters
  - discussion
parent: 1773
depends_on: []
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
claimed: false
---

## Observation
User feedback after #1797 compact filters: the Kanban header/status sequence is strange and partly redundant.

Current unfiltered: `124 tasks | Filters`.
Current filtered example: `91 matching | Filters (1) | 91 / 124 tasks | Clear filters | Tags: ux-feedback`.

## User Choice
After options review, the user selected option B: make the primary counter become the ratio when filtered.

## Desired Direction
Use the large counter as the single count source:
- Unfiltered: `124 tasks`.
- Filtered: `91 / 124 tasks`.
- Remove the separate result-count pill/text.
- Keep active filter chips, filter toggle, and clear filters action without duplicating the count.

## Value
The header should be scannable and avoid competing count labels. The filter state should explain *why* the board is narrowed while the counter explains *how much* remains.

## Acceptance Criteria
- Kanban header has only one task-count source.
- Unfiltered state still reads as the full task count.
- Filtered state changes the primary count to `visible / total tasks`.
- The separate `matching` / result-count summary is removed or hidden from the visual header.
- Filter toggle, active filter chips, and clear-filters command remain available.
- Existing filter behavior remains unchanged.
- Screenshot proof captures the filtered header at the 1024 support floor.

[[2026-05-24T06:22:00+02:00]]
## Implementation Proof
- Updated the Kanban header metric so the unfiltered state remains `N tasks` and the filtered state becomes `visible / total tasks`.
- Removed the visible duplicate `filter-result-count` pill while preserving the hidden aria-live region for filter announcements.
- Ordered the visible filtered header as primary ratio, active filter chips, `Filters (n)`, and `Clear filters`.
- Existing filter behavior stayed unchanged, including PDS tag filtering.
- Focused tests passed: `npm test -- --run src/__tests__/KanbanBoard.test.tsx src/__tests__/KanbanBoard.filter-integration.test.tsx src/__tests__/KanbanBoard.filter-e2e.test.tsx src/__tests__/FilterAccessibility.test.tsx src/__tests__/FilterPanel.test.tsx` -> 122 passed.
- Lint passed: `npx eslint src/KanbanBoard.tsx src/__tests__/KanbanBoard.filter-integration.test.tsx src/__tests__/KanbanBoard.filter-e2e.test.tsx e2e/filter-controls.spec.ts`.
- Build passed: `npm run build` (known Vite chunk-size warning only).
- Reader proof screenshot: `.owlbear/scratch/1716-wide-cockpit/1801-kanban-filter-summary-1024.png` at the 1024 support floor. Metrics confirmed header summary `1 / 3 tasks`, active chip `Tags: ux-feedback`, no visible `filter-result-count`, hidden live region `1 / 3 tasks`, tag value `["ux-feedback"]`, and visible card IDs `["1"]`.

[[2026-05-24T06:22:10+02:00]]
Completed the simplified Kanban filter summary counter with behavioral and reader proof.
