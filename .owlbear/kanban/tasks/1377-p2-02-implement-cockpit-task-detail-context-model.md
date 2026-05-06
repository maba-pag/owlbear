---
id: 1377
title: 'P2-02: Implement Cockpit task detail context model'
status: backlog
priority: critical
created: 2026-05-06T01:04:31.145299+00:00
updated: 2026-05-06T01:06:57.253247+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- task-detail
- model
parent: 1363
depends_on:
- 1376
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement the Cockpit task detail frontend model needed for safe detail-view decisions.

## Problem Evidence
- DetailTab TaskDetail omits backend task fields such as claimed, claimed_at, and claimed_by.
- Dependency and parent context is not available enough for action gating and edit decisions.
- Missing context can be confused with a user clearing a value.

## Acceptance Criteria
- The task detail frontend model matches backend task detail fields needed for Cockpit decisions, including claim state.
- Dependency and parent context from the backend is preserved for UI decisions wherever the backend exposes it.
- Optional or unavailable context has an explicit state and is not converted into a clearing edit.
- Existing valid task fetch, edit, and move flows continue to work with the expanded model.
- The implementation satisfies #1376 without adding action-gating or validation behavior owned by later tasks.

## Scope
- In scope: Cockpit frontend task detail model, parsing, and state propagation.
- Out of scope: edit validation, dirty-state UX, action gating, conflict resolution, backend lifecycle work, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1376.
