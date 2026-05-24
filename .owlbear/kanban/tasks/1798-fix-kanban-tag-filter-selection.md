---
id: 1798
title: Fix Kanban tag filter selection
status: done
priority: critical
created: 2026-05-24T05:50:33.420550+02:00
updated: 2026-05-24T05:56:29.921871+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - filters
  - bug
  - discussion
parent: 1773
depends_on: []
ac:
  - Selecting one or more tag filter entries visibly persists the selected 
    values.
  - Selected tag filters reduce the visible Kanban cards to matching tasks.
  - Clearing filters removes selected tag state and restores all matching cards.
  - Regression tests cover tag filter selection and filtering behavior.
  - Screenshot proof captures selected tags and filtered board state.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
User feedback from #1784 discussion: Kanban tag filter does not appear to work. Selecting entries shows no visible filtering, selected tags do not stick, and the selection gets lost.

## Current Interpretation
This is likely a behavior/state binding bug in the tag filter control, not only a visual issue.

## Value
Tag filtering is a core board navigation workflow; selections must visibly stick and immediately affect the card set.

## User Direction
User asked to save and address this before starting other new work.

[[2026-05-24T05:56:22+02:00]]
## Implementation Proof
- Root cause: Kanban tag filter listened only for the legacy/internal `update` event. PDS `PMultiSelect` emits the canonical `change` event with `detail.value`, so real selections did not persist.
- Fix: tag filter now handles both `update` and `change`, matching the PDS wrapper contract and the Memory tab pattern.
- Focused tests passed: `npm test -- --run src/__tests__/FilterPanel.test.tsx src/__tests__/FilterPanel.pds-controls.test.tsx src/__tests__/KanbanBoard.filter-e2e.test.tsx src/__tests__/KanbanBoard.filter-integration.test.tsx src/__tests__/filterTasks.test.ts` -> 100 passed.
- Lint passed: `npx eslint src/components/FilterPanel.tsx src/__tests__/FilterPanel.test.tsx src/__tests__/KanbanBoard.filter-e2e.test.tsx`.
- Build passed: `npm run build` (known Vite chunk-size warning only).
- Reader proof screenshot: `.owlbear/scratch/1716-wide-cockpit/1798-kanban-tag-filter-1024.png` at 1024px. Metrics: tag value `["alpha"]`, result `2 / 3 tasks`, visible card IDs `["1", "3"]`, beta hidden.

[[2026-05-24T05:56:29+02:00]]
Fixed tag filter persistence by handling the PDS multi-select change event. Verified selected tags stick, filter the board, clear/reset paths remain covered, focused tests/lint/build passed, and 1024 screenshot proof captured.
