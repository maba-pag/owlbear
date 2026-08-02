---
id: 1797
title: Make Kanban filter controls compact
status: archived
priority: medium
created: 2026-05-24T05:50:26.668023+02:00
updated: 2026-05-24T10:50:02.586236+02:00
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
  - Kanban filter fields use compact control treatment where available.
  - Filter layout remains readable and aligned at the 1024px support floor.
  - Existing filter behavior remains unchanged except for density/polish.
  - Screenshot proof captures the compact filter panel.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User feedback from #1784 discussion: Kanban filter fields are huge; compact treatment would likely be better.

## Current Interpretation
The filter panel controls are consuming too much vertical and visual space for a repeated filtering workflow.

## Value
Filtering should feel like a lightweight board tool, not a large form.

## User Direction
User asked to save and address this before starting other new work.

[[2026-05-24T05:59:01+02:00]]
## Implementation Proof
- Applied PDS `compact` variants to the Kanban filter search, priority select, tag multi-select, and blocked checkbox controls.
- Preserved existing filter behavior, including the #1798 tag-selection `change` event path.
- Focused tests passed: `npm test -- --run src/__tests__/FilterPanel.test.tsx src/__tests__/FilterPanel.pds-controls.test.tsx src/__tests__/KanbanBoard.filter-e2e.test.tsx src/__tests__/KanbanBoard.filter-integration.test.tsx` -> 82 passed.
- Lint passed: `npx eslint src/components/FilterPanel.tsx src/__tests__/FilterPanel.pds-controls.test.tsx`.
- Build passed: `npm run build` (known Vite chunk-size warning only).
- Reader proof screenshot: `.owlbear/scratch/1716-wide-cockpit/1797-kanban-compact-filters-1024.png` at the 1024 support floor. Metrics confirmed compact controls, selected tag value `["alpha"]`, result `2 / 3 tasks`, and visible card IDs `["1", "3"]`.

[[2026-05-24T05:59:09+02:00]]
Completed compact Kanban filter controls using PDS compact variants. Verified focused filter tests, lint, build, and 1024 screenshot proof with tag filtering still active.
