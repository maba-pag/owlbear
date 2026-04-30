---
id: 1228
title: Frontend — wire DetailTab + ActivityTab into sidecar
status: backlog
priority: needed
created: '2026-04-30 16:31:18.636409+00:00'
updated: '2026-04-30 16:33:23.440319+00:00'
tags:
- cockpit
- frontend
- feature
parent:
depends_on:
- 1225
- 1223
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Connect the existing DetailTab and ActivityTab components to the sidecar shell, making them functional.

## Acceptance Criteria
- [ ] Clicking a task Card sets it as selected (visual highlight + state)
- [ ] Selected task data fetched via GET /api/tasks/{id} and passed to DetailTab
- [ ] DetailTab rendered in sidecar "Detail" tab with full task info, edit capability
- [ ] ActivityTab rendered in sidecar "Activity" tab with session data
- [ ] Dead adapter functions removed from `adapter.py` (list_tasks, show_task, board_config, list_sessions)
- [ ] `/hello` route removed from Shell.tsx
- [ ] Clicking a different card updates the detail panel

## Files
- `serve/cockpit/web/src/Shell.tsx`
- `serve/cockpit/web/src/components/Card.tsx`
- `serve/cockpit/web/src/components/DetailTab.tsx`
- `serve/cockpit/web/src/components/ActivityTab.tsx`
- `serve/cockpit/src/owlbear_cockpit/adapter.py`
