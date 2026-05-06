---
id: 1382
title: 'P2-07: Test Cockpit task conflict resolution workflow'
status: backlog
priority: needed
created: 2026-05-06T01:04:39.067978+00:00
updated: 2026-05-06T01:06:57.282369+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:test
- frontend
- conflict-resolution
- error-handling
parent: 1363
depends_on:
- 1381
- 1375
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write frontend tests for safe 409 conflict resolution in the task detail editor.

## Problem Evidence
- The conflict modal fetches the latest task and resets local form state.
- The modal still shows Force save, which can discard local edits while implying the local edit will be forced.
- Expected mutation errors must use the frontend error contract from #1375.

## Acceptance Criteria
- Tests prove local edits are preserved when a 409 conflict response triggers a latest-task refresh.
- Tests prove the UI shows enough remote-versus-local context for the user to understand the conflict.
- Tests prove force-save is available only after an explicit overwrite choice and sends the user's preserved local intended changes.
- Tests prove canceling or dismissing conflict resolution does not silently discard local edits.
- Tests prove 409, 404, 422, and broader expected mutation errors use the frontend error contract from #1375.
- The proof fails against the audited reset-then-force behavior and is suitable for #1383 to satisfy.

## Scope
- In scope: Cockpit frontend task detail conflict-resolution tests for edit conflicts.
- Out of scope: action gating from #1381, backend conflict semantics, decision resolution, global accessibility audit, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1383.
