---
id: 1501
title: 'Cockpit: Implement api/tasks.ts module'
status: backlog
priority: needed
created: 2026-05-12T02:43:28.689799+00:00
updated: 2026-05-12T04:24:15.279011+00:00
tags:
  - cockpit
  - frontend
parent: 1493
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\nCreate `serve/cockpit/web/src/api/tasks.ts` with centralized API functions following the existing `repair.ts`/`cleanup.ts` pattern.\n\n## Acceptance Criteria\n- Exports `getTask()`, `moveTask()`, `editTask()`, `releaseTask()` async functions\n- Exports `ApiError` class with `.status` property\n- All functions use `getResponseErrorMessage` for error parsing and throw `ApiError` on non-ok responses\n- Request/response types exported and match backend contract\n- Unit tests cover success and error paths for each function\n\n## Implementation Notes\n- Follow existing pattern in `api/repair.ts` and `api/cleanup.ts`\n- `ApiError` may live in a shared `api/errors.ts` if cleaner
2026-05-12T04:24:15+00:00
Moved to backlog for architecture review. Task was placed in `todo` directly by researcher without arch review or proof-bundle assignment. AC has B3 violations ("All functions") that need refinement. Proof bundle needs assignment.