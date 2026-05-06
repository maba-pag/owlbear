---
id: 1376
title: 'P2-01: Test Cockpit task detail context model'
status: backlog
priority: critical
created: 2026-05-06T01:04:29.741762+00:00
updated: 2026-05-06T01:06:57.230780+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:test
- frontend
- task-detail
- model
parent: 1363
depends_on:
- 1367
- 1375
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write frontend tests proving Cockpit task detail state includes the backend context needed for safe UI decisions.

## Problem Evidence
- DetailTab TaskDetail omits backend task fields such as claimed, claimed_at, and claimed_by.
- Dependency and parent context is not available enough for action gating and edit decisions.
- Missing context can be confused with a user clearing a value.

## Acceptance Criteria
- Tests prove the frontend task detail model exposes claim state fields: claimed, claimed_at, and claimed_by.
- Tests prove dependency and parent context returned by the backend is available to task-detail decision logic where the backend provides it.
- Tests prove absent optional context is represented explicitly and is never treated as an editable clearing change.
- Tests cover state combinations needed by downstream action gating: unclaimed, claimed, blocked, and dependency-constrained tasks.
- The proof fails against the audited incomplete detail model and is suitable for #1377 to satisfy.

## Scope
- In scope: Cockpit frontend task detail type, hook, and component-state tests.
- Out of scope: parent/dependency edit validation, action gating, conflict resolution, backend schema changes, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1377.
