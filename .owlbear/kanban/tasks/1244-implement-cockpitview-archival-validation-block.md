---
id: 1244
title: 'Implement: CockpitView archival validation block'
status: todo
priority: important
created: 2026-05-01T03:08:05.317883+00:00
updated: 2026-05-01T03:11:04.517278+00:00
tags:
- scope:backend
parent: 1238
depends_on:
- 1240
- 1243
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `CockpitView.move_task` validates all archival conditions when `status == "archived"`:
  - `archival_reason` is required; raises `ERR_ARCHIVAL_REASON_REQUIRED` when absent
  - `archival_refs` forbidden for `completed`, `dropped`, `wontfix`; raises `ERR_ARCHIVAL_REFS_FORBIDDEN`
  - `archival_refs` required for `deprecated`, `duplicate`; raises `ERR_ARCHIVAL_REFS_REQUIRED`
  - `completed` requires `task.status == "done"` before the move; raises `ERR_COMPLETED_REQUIRES_DONE`
  - Each ref ID must exist on the board; raises a 422 error for non-existent refs
  - Task cannot reference itself in `archival_refs`; raises a 422 error
  - Ref chain must not loop back to the task; raises a 422 error for cycles
- Errors are raised as engine error codes and surface as 422 responses via the route
- All tests from #1240 pass

## In Scope

- `CockpitView.move_task` validation block in the cockpit `engine.py`

## Out of Scope

- `MoveRequest`/route layer (already done by #1243)
- Engine-level archival persistence (already complete)

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Backend Changes B3