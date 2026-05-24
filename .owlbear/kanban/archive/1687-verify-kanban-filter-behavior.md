---
id: 1687
title: Verify kanban filter behavior
status: archived
priority: important
created: 2026-05-21T19:52:36.134394+02:00
updated: 2026-05-24T10:50:01.078241+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - filters
  - behavior
parent:
depends_on: []
ac:
  - Reproduce Kanban filter behavior with realistic task data.
  - Classify any failures as observed current defects or not reproduced.
  - Fix confirmed filter failures or simplify low-value filter controls.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Kanban filters may not actually work; user vaguely remembers they did not.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-suspected behavior defect; requires reproduction before treating as confirmed.
- Value question: filters are only worth their UI weight if they reliably narrow the board and clearly indicate active constraints.
- Browser target: priority/tag/blocked/search/status filters with realistic tasks.

## Acceptance Criteria
- Reproduce filter behavior using realistic board data and screenshots.
- Confirm whether each filter changes visible cards and header/filter counts as expected.
- Fix real failures; remove or simplify filters that do not provide reliable value.

## Completion Evidence
- Reproduced Kanban filtering against realistic Cockpit task data: the real backend returned 43 tasks, and active filters narrowed the board to 3 matching tasks.
- Search, priority, tags, and blocked filters are confirmed working in focused unit/integration coverage and Playwright browser workflows. Active dimensions compose with AND semantics and update visible cards, empty-column placeholders, result counts, reset state, and aria-live announcements.
- Product classification: no real data-filter defect was reproduced. The only browser failure observed was a test false positive: Playwright pierces open PDS shadow DOM, so `#filter-panel input[type="checkbox"]` matched the internal `p-checkbox` input. The assertion now verifies that no duplicate light-DOM native checkbox fallback exists.
- Product improvement: active filter constraints are now named in the Kanban header as chips, so a narrowed board explains itself instead of relying only on `Filters (N)` and `M / N tasks` counts.
- Status filter decision: not added. Status is already the board's primary column dimension, so a separate status filter would duplicate the main layout unless future user evidence shows a concrete workflow need.
- Screenshot evidence: `.owlbear/scratch/1716-wide-cockpit/kanban-filters-1687.png` shows the real 2560px Cockpit with `Search: filter`, `Priority: Important`, `3 matching`, and `3 / 43 tasks` visible.

## Verification
- `npx vitest run src/__tests__/filterTasks.test.ts src/__tests__/FilterPanel.test.tsx src/__tests__/FilterPanel.pds-controls.test.tsx src/__tests__/KanbanBoard.filter-e2e.test.tsx src/__tests__/FilterAccessibility.test.tsx --reporter=json --outputFile=/Users/markus/Projects/owlbear-dev/.owlbear/scratch/1687-vitest-filter.json` -> 31 suites, 99 tests passed.
- `npm run test:e2e:all -- e2e/filter-controls.spec.ts --reporter=json > /Users/markus/Projects/owlbear-dev/.owlbear/scratch/1687-e2e-filter.json` -> 36 expected, 0 unexpected.
- `npx eslint src/KanbanBoard.tsx src/__tests__/KanbanBoard.filter-e2e.test.tsx e2e/filter-controls.spec.ts` -> passed.
- `npm run build` -> passed; existing Vite large-chunk warning only.
