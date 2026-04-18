---
id: 933
title: 'P2-05: GREEN — Kanban board surface'
status: research
priority: important
created: 2026-04-17T19:58:25.632962+00:00
updated: 2026-04-17T19:58:25.632962+00:00
tags:
- cockpit
- frontend
- phase-2
- type:build
parent: 920
depends_on:
- 931
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Implement the kanban board surface to pass RED tests from #931.

## Acceptance Criteria

- [ ] Board fetches data from `GET /api/board` + `GET /api/tasks` (via TanStack Query or fetch hooks)
- [ ] Status columns rendered in board config order via CSS Grid or flexbox
- [ ] Cards sorted by priority within columns; ~48-56px card height
- [ ] Card indicators: priority-coded left border, block badge (icon + tooltip with block_reason), running indicator (derived from claim_status in API response)
- [ ] Drag-to-move: uses `valid_transitions` to highlight valid target columns; drop calls `POST /api/tasks/{id}/move`
- [ ] Context menu on right-click/long-press offers all valid status transitions for long-distance moves
- [ ] Horizontal scroll between columns; vertical scroll within columns
- [ ] Column headers show task counts
- [ ] Designed empty state per column, loading skeleton, and error recovery state
- [ ] Status bar wired: traffic-light reflects poll health; per-column counts update
- [ ] All RED tests from #931 pass

## Files

- `serve/cockpit/web/src/surfaces/kanban/KanbanBoard.tsx`
- `serve/cockpit/web/src/surfaces/kanban/Column.tsx`
- `serve/cockpit/web/src/surfaces/kanban/Card.tsx`
- `serve/cockpit/web/src/surfaces/kanban/ContextMenu.tsx`
- `serve/cockpit/web/src/hooks/useBoard.ts` (or similar data hook)