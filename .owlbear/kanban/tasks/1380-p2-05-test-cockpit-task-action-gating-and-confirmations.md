---
id: 1380
title: 'P2-05: Test Cockpit task action gating and confirmations'
status: backlog
priority: needed
created: 2026-05-06T01:04:35.632458+00:00
updated: 2026-05-06T01:06:57.266658+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:test
- frontend
- task-actions
- workflow
parent: 1363
depends_on:
- 1379
- 1375
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write frontend tests for task action visibility, enablement, and action-specific confirmations.

## Problem Evidence
- DetailTab renders Unclaim even for unclaimed tasks, causing avoidable backend 409 responses.
- Move backward, unblock, unclaim, and destructive-ish actions need state-aware gating and clear consequences.
- Confirmation dialogs are generic and lack action-specific labels and focus semantics.

## Acceptance Criteria
- Tests prove action buttons are shown or enabled only when valid for the current task status, claim state, block state, and backend transition rules.
- Tests prove Unclaim is unavailable for unclaimed tasks and does not issue a mutation in that state.
- Tests prove unblock and move-backward actions require valid state and show action-specific confirmation text.
- Tests prove confirmation labels name the concrete action and target state instead of using generic Confirm text.
- Tests include keyboard/focus expectations for the confirmation workflow, leaving the final global accessibility gate to a separate task.
- Tests prove expected 409, 404, and 422 responses use the frontend error contract from #1375.
- The proof fails against the audited always-rendered action behavior and is suitable for #1381 to satisfy.

## Scope
- In scope: Cockpit frontend task action gating and confirmation tests.
- Out of scope: conflict resolution, decision resolution, backend route changes, global accessibility audit, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1381.
