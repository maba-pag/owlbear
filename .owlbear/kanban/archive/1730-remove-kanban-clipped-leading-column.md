---
id: 1730
title: Remove Kanban clipped leading column sliver
status: archived
priority: important
created: 2026-05-23T03:36:07+0200
updated: 2026-05-24T10:50:01.675487+02:00
tags:
  - cockpit
  - kanban
  - layout
  - ux-feedback
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
type: bug
assignee: copilot
---

## Problem
After the board auto-aligns toward the populated Done column, the left edge of the Kanban strip can show only a narrow clipped sliver of the previous column count. It reads like an accidental layout crop rather than a deliberate scroll position.

## Acceptance Criteria
- Initial Kanban auto-alignment lands on a clean column boundary or otherwise avoids showing a tiny clipped leading column fragment.
- The first non-empty column remains visible on boards where populated work is in later statuses.
- Horizontal scrolling and all configured columns remain available.
- Add or update focused tests for the auto-scroll calculation.
- Capture after-fix screenshot or metrics evidence.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1729-kanban-bounded-after.png` shows the far-left clipped column-count sliver before the Todo column.

## Evidence After Fix
- Kanban strip now keeps extra trailing scroll padding so browser max-scroll can clear the previous column fragment while preserving all columns and horizontal scrolling.
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1730-kanban-leading-column-after.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1730-kanban-leading-column-after-metrics.json` reports `visibleLeadingFragment: null`, `documentScrollHeight: 1000`, `viewportHeight: 1000`, and full visible widths for Todo through Done.
- Focused Vitest passed: `src/__tests__/KanbanBoard.test.tsx`, 39 tests.
- ESLint passed for `src/KanbanBoard.tsx` and `src/__tests__/KanbanBoard.test.tsx`.
- `npm run build` passed with the existing Vite chunk-size warning.
