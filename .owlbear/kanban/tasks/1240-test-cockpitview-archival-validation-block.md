---
id: 1240
title: 'Test: CockpitView archival validation block'
status: todo
priority: needed
created: 2026-05-01T03:07:52.852822+00:00
updated: 2026-05-01T03:10:07.486383+00:00
tags:
- scope:backend
parent: 1238
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `CockpitView.move_task` with `status="archived"` and `archival_reason=None` raises `ERR_ARCHIVAL_REASON_REQUIRED` (422)
- `CockpitView.move_task` with `reason="completed"` and non-empty `archival_refs` raises `ERR_ARCHIVAL_REFS_FORBIDDEN`
- `CockpitView.move_task` with `reason="dropped"` and non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN`
- `CockpitView.move_task` with `reason="wontfix"` and non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN`
- `CockpitView.move_task` with `reason="deprecated"` and empty refs raises `ERR_ARCHIVAL_REFS_REQUIRED`
- `CockpitView.move_task` with `reason="duplicate"` and empty refs raises `ERR_ARCHIVAL_REFS_REQUIRED`
- `CockpitView.move_task` with `reason="completed"` when `task.status != "done"` raises `ERR_COMPLETED_REQUIRES_DONE`
- `CockpitView.move_task` raises a 422 error when any ref ID does not exist on the board
- `CockpitView.move_task` raises a 422 error when `archival_refs` contains the task's own ID (self-reference)
- `CockpitView.move_task` raises a 422 error when `archival_refs` creates a dependency cycle
- Valid archival (e.g., `reason="completed"`, task `status == "done"`, empty refs) succeeds and persists both fields

## In Scope

- All validation paths in `CockpitView.move_task` for the `status == "archived"` case

## Out of Scope

- Non-archival moves (plain status changes)
- `MoveRequest`/route layer (B1+B2 task #1239)

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Backend Changes B3