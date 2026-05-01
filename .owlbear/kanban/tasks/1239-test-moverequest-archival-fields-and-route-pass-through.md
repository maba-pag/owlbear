---
id: 1239
title: 'Test: MoveRequest archival fields and route pass-through'
status: todo
priority: needed
created: 2026-05-01T03:07:50.539456+00:00
updated: 2026-05-01T03:09:58.277155+00:00
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

- `MoveRequest` with no `archival_reason`/`archival_refs` fields deserialises correctly (backwards-compatible)
- `MoveRequest` with `archival_reason="completed"` and `archival_refs=[1, 2]` deserialises with correct types and defaults
- `extra="forbid"` still rejects unknown fields (no regression)
- Move route handler calls `view.move_task()` with `archival_reason` and `archival_refs` forwarded from the request
- Move route with default values (`archival_reason=None`, `archival_refs=[]`) passes through without error

## In Scope

- `MoveRequest` Pydantic model field tests
- Route pass-through tests against a mocked `CockpitView`

## Out of Scope

- `CockpitView` validation logic (B3 task #1240)
- Engine-level archival behaviour (already tested)

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Backend Changes B1, B2