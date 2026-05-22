---
id: 1718
title: Default cockpit lists to useful sorting
status: done
priority: important
created: 2026-05-22T01:01:18.310876+02:00
updated: 2026-05-22T14:20:12+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - sorting
  - kanban
  - decisions
  - memory
parent:
depends_on: []
ac:
  - Sort Kanban tasks within columns by priority descending, then updated
    timestamp descending, unless a user-selected sort overrides it.
  - Sort pending Decisions oldest first by created timestamp.
  - Sort Memory entries by confidence descending by default.
  - Add focused tests proving the default order for each route with ties and
    malformed/missing values handled predictably.
  - Validate with desktop screenshots at widths >= 1200px.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Default route ordering should match how the cockpit is used: Kanban tasks could sort by priority first, highest first, then last edit newest first; Decisions should sort oldest first by creation date; Memories should sort by highest confidence.

## Evaluation Notes
- Classification: user-observed workflow-ordering request, not theoretical.
- Impact: hurts Cockpit now if the first visible items are not the most actionable or trustworthy for each tab.
- Decisions oldest-first is also tracked on #1710 because it belongs to the current Decisions IA pass.

## Acceptance Criteria
- Sort Kanban tasks within columns by priority descending, then updated timestamp descending, unless a user-selected sort overrides it.
- Sort pending Decisions oldest first by created timestamp.
- Sort Memory entries by confidence descending by default.
- Add focused tests proving the default order for each route with ties and malformed/missing values handled predictably.
- Validate with desktop screenshots at widths >= 1200px.

## Builder Evidence
- Implemented default Kanban column sorting by semantic priority descending, then updated timestamp descending, then task id ascending for deterministic ties. Malformed priorities and timestamps are treated as lowest-ranked values.
- Implemented pending Decisions ordering by created timestamp ascending, with malformed timestamps last and decision id as the deterministic tie-break.
- Implemented Memory ordering by confidence descending, then state priority, created timestamp ascending, and id tie-break. Malformed confidence values sort after finite confidence values without producing `NaN` comparator ties.
- Focused tests: `npx vitest run src/__tests__/Column.test.tsx src/__tests__/DecisionsPage_1688.test.tsx src/__tests__/MemoryTab_1671.test.tsx --reporter=json --outputFile=/Users/markus/Projects/owlbear-dev/.owlbear/scratch/1718-vitest-sorting.json` -> 65 passed, 0 failed.
- Board integration: `npx vitest run src/__tests__/KanbanBoard.test.tsx --reporter=dot` -> 38 passed, 0 failed.
- Lint: `npx eslint src/components/Column.tsx src/pages/DecisionsPage.tsx src/pages/MemoryTab.tsx src/__tests__/Column.test.tsx src/__tests__/DecisionsPage_1688.test.tsx src/__tests__/MemoryTab_1671.test.tsx` -> pass.
- Build: `npm run build` -> pass; existing Vite chunk-size warning only.
- Editor diagnostics clean for all touched source and test files.
- Desktop screenshot validation at 2560x1440: `.owlbear/scratch/1716-wide-cockpit/kanban-viewport.png`, `.owlbear/scratch/1716-wide-cockpit/decisions-viewport.png`, and `.owlbear/scratch/1716-wide-cockpit/memories-viewport.png`. Capture reported 0 console errors, 0 page errors, and 0 response errors.