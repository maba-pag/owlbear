---
id: 1246
title: 'Implement: handleTransitionClick archive intercept'
status: todo
priority: important
created: 2026-05-01T03:08:09.832815+00:00
updated: 2026-05-01T03:11:09.453738+00:00
tags:
- scope:frontend
parent: 1238
depends_on:
- 1242
- 1245
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `handleTransitionClick` opens `ArchivalModal` instead of immediately posting when `targetStatus === "archived"`
- Props passed to `ArchivalModal`: `taskId`, `taskStatus` (from `task.status`), `expectedUpdated` (from `task.updated` frozen at context-menu-open time)
- `expectedUpdated` is not re-read from a polling-updated task reference while the modal is open
- Non-archival transitions are unchanged
- All tests from #1242 pass

## In Scope

- `KanbanBoard.tsx`: `handleTransitionClick` function and modal open/close state

## Out of Scope

- `ArchivalModal` internals (already done by #1245)
- Backend changes

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Frontend Changes F3