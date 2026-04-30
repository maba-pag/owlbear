---
id: 1229
title: Frontend — complete drag-and-drop (call move API on drop)
status: backlog
priority: needed
created: '2026-04-30 16:31:18.646741+00:00'
updated: '2026-04-30 16:33:23.445472+00:00'
tags:
- cockpit
- frontend
- feature
parent:
depends_on:
- 1225
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Make drag-and-drop functional — dropping a card on a valid column triggers a move.

## Acceptance Criteria
- [ ] Dragging a card stores its taskId and updated token in state
- [ ] Dropping on a valid target column calls POST /api/tasks/{id}/move with the target status
- [ ] On success: refetchTasks(), clear drag state
- [ ] On 409 (stale): show error message, refetch to get fresh data
- [ ] On other error: show error, no state change
- [ ] Dropping on invalid target does nothing (existing highlight behavior preserved)

## Files
- `serve/cockpit/web/src/components/Column.tsx`
- `serve/cockpit/web/src/KanbanBoard.tsx`
