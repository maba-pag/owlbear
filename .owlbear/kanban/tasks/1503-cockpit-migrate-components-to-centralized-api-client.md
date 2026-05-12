---
id: 1503
title: 'Cockpit: Migrate components to centralized API client'
status: backlog
priority: needed
created: 2026-05-12T02:43:28.748468+00:00
updated: 2026-05-12T04:24:15.257969+00:00
tags:
  - cockpit
  - frontend
parent: 1493
depends_on:
  - 1501
  - 1502
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\nReplace all raw `fetch()` calls to `/api/tasks` and `/api/decisions` endpoints in component files with imported functions from `api/tasks.ts` and `api/decisions.ts`.\n\n## Acceptance Criteria\n- No raw `fetch()` to `/api/tasks/*` or `/api/decisions/*` remains in component files (KanbanBoard, DetailTab, ArchivalModal, ResolveModal, Shell)\n- All existing tests pass without modification (behavioral preservation)\n- Abort signal support, conflict resolution, and error handling behavior unchanged\n- No new dependencies introduced beyond the api/ modules\n\n## Implementation Notes\n- Preserve all existing behavior exactly — this is a refactor, not a feature change\n- Components: KanbanBoard, DetailTab, ArchivalModal, ResolveModal, Shell\n- Verify abort signals are threaded through correctly
2026-05-12T04:24:15+00:00
Moved to backlog for architecture review. Task was placed in `todo` directly by researcher without arch review or proof-bundle assignment. AC has B3 violations ("All existing tests") and banned word "No" used as naked quantifier. Proof bundle needs assignment.