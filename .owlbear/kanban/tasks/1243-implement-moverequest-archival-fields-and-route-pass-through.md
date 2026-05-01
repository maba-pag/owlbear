---
id: 1243
title: 'Implement: MoveRequest archival fields and route pass-through'
status: todo
priority: needed
created: 2026-05-01T03:08:02.839683+00:00
updated: 2026-05-01T03:11:02.148445+00:00
tags:
- scope:backend
parent: 1238
depends_on:
- 1239
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `MoveRequest` has `archival_reason: str | None = None` and `archival_refs: list[int] = []` fields
- `extra="forbid"` is preserved on `MoveRequest` (unknown fields are still rejected)
- Move route handler passes `req.archival_reason` and `req.archival_refs` through to `view.move_task()`
- Existing move requests without archival fields are unaffected (backwards-compatible)
- All tests from #1239 pass

## In Scope

- `routes/mutation.py`: `MoveRequest` model and move handler

## Out of Scope

- `CockpitView` validation logic (B3 task #1244)
- Frontend changes

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Backend Changes B1, B2