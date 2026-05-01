---
id: 1242
title: 'Test: handleTransitionClick archive intercept'
status: todo
priority: needed
created: 2026-05-01T03:07:57.562942+00:00
updated: 2026-05-01T03:10:26.274400+00:00
tags:
- scope:frontend
parent: 1238
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Clicking the `→ archived` transition in the context menu opens `ArchivalModal`; no `POST /api/tasks/{id}/move` fires immediately
- All other status transitions (e.g., `→ done`, `→ in-progress`) remain unaffected — they still fire the move request immediately
- `ArchivalModal` receives `taskId`, `taskStatus`, and `expectedUpdated` as props
- `expectedUpdated` equals `task.updated` frozen at context-menu-open time — not re-read from a polling-updated task reference after the menu opens

## In Scope

- `handleTransitionClick` conditional branch for `targetStatus === "archived"`
- Prop forwarding to `ArchivalModal`

## Out of Scope

- `ArchivalModal` internal behaviour (F2 task #1241)
- Backend archival flow

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Frontend Changes F3