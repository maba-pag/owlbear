---
id: 1381
title: 'P2-06: Implement Cockpit task action gating and confirmations'
status: backlog
priority: needed
created: 2026-05-06T01:04:37.405026+00:00
updated: 2026-05-06T01:06:57.276277+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- task-actions
- workflow
parent: 1363
depends_on:
- 1380
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement state-aware task action gating and action-specific confirmations in Cockpit task detail.

## Problem Evidence
- DetailTab renders Unclaim even for unclaimed tasks, causing avoidable backend 409 responses.
- Move backward, unblock, unclaim, and destructive-ish actions need state-aware gating and clear consequences.
- Confirmation dialogs are generic and lack action-specific labels and focus semantics.

## Acceptance Criteria
- Action buttons are shown or enabled only when valid for the current task status, claim state, block state, and backend transition rules.
- Unclaim is unavailable for unclaimed tasks and cannot issue a mutation in that state.
- Unblock and move-backward actions expose clear action-specific confirmation text before mutating state.
- Confirmation labels name the concrete action and target state instead of using generic Confirm text.
- Confirmation keyboard and focus behavior meets the expectations captured in #1380, with final global accessibility verification left to a separate task.
- Expected 409, 404, and 422 responses use the frontend error contract from #1375.
- The implementation satisfies #1380 without changing conflict-resolution behavior owned by #1383.

## Scope
- In scope: Cockpit frontend task action gating and confirmation behavior.
- Out of scope: conflict resolution, decision resolution, backend route changes, global accessibility audit, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1380.
