---
id: 931
title: 'P2-04: RED — Kanban board surface tests'
status: research
priority: important
created: 2026-04-17T19:58:06.421846+00:00
updated: 2026-04-17T19:58:06.421846+00:00
tags:
- cockpit
- frontend
- phase-2
- type:test
parent: 920
depends_on:
- 929
- 930
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Write failing tests for the kanban board surface: status columns, task cards, drag-to-move, context menu, and visual indicators.

## Acceptance Criteria

- [ ] Test file(s) for kanban board components (Vitest + React Testing Library)
- [ ] Tests cover:
  - Board renders status columns in board config order (from `GET /api/board`)
  - Cards render within correct columns, sorted by priority
  - Card shows: truncated title, priority-coded left border colour, block badge (with reason tooltip), running indicator (from claim_status)
  - Card density ~48-56px height
  - Drag-to-move: valid target columns highlight based on `valid_transitions`; invalid targets dim
  - Context menu on card offers all valid status transitions for that card's current status
  - Board header shows per-column task counts
  - Empty column renders designed empty state (not blank)
  - Loading state renders skeleton or spinner (not white screen)
  - Error state (API failure) renders recovery message
  - Horizontal scroll between columns; vertical scroll within columns
- [ ] All tests fail (RED phase)

## Files

- `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` (or colocated)