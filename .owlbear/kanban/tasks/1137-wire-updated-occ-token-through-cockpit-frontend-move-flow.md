---
id: 1137
title: Wire updated OCC token through cockpit frontend move flow
status: research
priority: important
created: 2026-04-26T16:29:17.620093+00:00
updated: 2026-04-26T16:29:49.711287+00:00
tags:
- cockpit
parent:
depends_on:
- 1135
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
Objective: Update the cockpit frontend and read API to supply the updated OCC token for move requests, completing the end-to-end OCC wire-up started in #1135.

Context: #1135 makes MoveRequest.updated required on the backend. The frontend (KanbanBoard.tsx handleTransitionClick) sends only { status } and TaskSummaryOut (used by GET /api/tasks) lacks updated. The frontend will get 422 on every move until this is wired through.

Acceptance Criteria:
- [ ] AC1: TaskSummaryOut in serve/cockpit/src/owlbear_cockpit/models.py includes updated: str field
- [ ] AC2: GET /api/tasks response includes updated for each task
- [ ] AC3: Frontend Task interface in serve/cockpit/web/src/hooks/useBoard.ts includes updated: string
- [ ] AC4: handleTransitionClick in KanbanBoard.tsx includes updated from the task object in the move request body
- [ ] AC5: Frontend test in KanbanBoard.test.tsx updated to assert updated is included in the POST /move request body
- [ ] AC6: E2E move flow works without 422 (manual or Playwright verification)

Likely files:
- serve/cockpit/src/owlbear_cockpit/models.py
- serve/cockpit/src/owlbear_cockpit/routes/read.py
- serve/cockpit/web/src/hooks/useBoard.ts
- serve/cockpit/web/src/KanbanBoard.tsx
- serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx