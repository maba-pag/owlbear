---
id: 1502
title: 'Cockpit: Implement api/decisions.ts module'
status: backlog
priority: needed
created: 2026-05-12T02:43:28.721141+00:00
updated: 2026-05-12T04:24:15.321874+00:00
tags:
  - cockpit
  - frontend
parent: 1493
depends_on:
  - 1501
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\nCreate `serve/cockpit/web/src/api/decisions.ts` with `resolveDR()` function following the established API client pattern.\n\n## Acceptance Criteria\n- Exports `resolveDR()` async function\n- Function is typed (request/response types exported)\n- Uses `getResponseErrorMessage` for error parsing, throws `ApiError` with `.status`\n- Unit tests cover success and error paths\n\n## Implementation Notes\n- Depends on `ApiError` from #1501 (either from `api/tasks.ts` or shared `api/errors.ts`)\n- Follow same pattern as `api/repair.ts`
2026-05-12T04:24:15+00:00
Moved to backlog for architecture review. Task was placed in `todo` directly by researcher without arch review or proof-bundle assignment. AC needs refinement (B3, numbering). Proof bundle needs assignment.