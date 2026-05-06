---
id: 1383
title: 'P2-08: Implement Cockpit task conflict resolution workflow'
status: backlog
priority: needed
created: 2026-05-06T01:04:40.670986+00:00
updated: 2026-05-06T01:06:57.287103+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- conflict-resolution
- error-handling
parent: 1363
depends_on:
- 1382
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement safe conflict resolution for task detail edits without discarding local intent.

## Problem Evidence
- The conflict modal fetches the latest task and resets local form state.
- The modal still shows Force save, which can discard local edits while implying the local edit will be forced.
- Expected mutation errors must use the frontend error contract from #1375.

## Acceptance Criteria
- Local edits are preserved when a 409 conflict response triggers a latest-task refresh.
- Conflict UI shows remote-versus-local context before the user chooses how to proceed.
- Force-save is available only after an explicit overwrite choice and sends the user's preserved local intended changes.
- Canceling or dismissing conflict resolution does not silently discard local edits.
- 409, 404, 422, and broader expected mutation errors use the frontend error contract from #1375.
- The implementation satisfies #1382 without changing backend conflict semantics or decision-resolution flows.

## Scope
- In scope: Cockpit frontend task detail conflict-resolution behavior for edit conflicts.
- Out of scope: action gating from #1381, backend conflict semantics, decision resolution, global accessibility audit, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1382.
