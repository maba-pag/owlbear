---
id: 1225
title: Frontend — split KanbanBoard into Card + Column + Board
status: backlog
priority: needed
created: '2026-04-30 16:31:18.609234+00:00'
updated: '2026-04-30 21:37:32.992050+00:00'
tags:
- cockpit
- frontend
- refactor
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Break the 270-line KanbanBoard.tsx monolith into focused component files.

## Acceptance Criteria
- [ ] `Card` component extracted to `serve/cockpit/web/src/components/Card.tsx`
- [ ] `Column` component extracted to `serve/cockpit/web/src/components/Column.tsx`
- [ ] `KanbanBoard.tsx` remains as orchestration (state, API calls, layout)
- [ ] All existing KanbanBoard tests pass without modification (or with minimal import updates)
- [ ] No functionality change

## Files
- `serve/cockpit/web/src/KanbanBoard.tsx`
- `serve/cockpit/web/src/components/Card.tsx` (new)
- `serve/cockpit/web/src/components/Column.tsx` (new)
