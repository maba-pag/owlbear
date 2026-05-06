---
id: 1363
title: Cockpit audit remediation
status: backlog
priority: critical
created: 2026-05-06T00:58:14.547083+00:00
updated: 2026-05-06T01:01:41.281392+00:00
tags:
- cockpit
- audit-remediation
- type:epic
- scope:cockpit
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Epic Purpose
Parent grouping for the approved Cockpit audit remediation follow-up across backend, frontend, design-system foundation, tests, docs, and delivery.

## Scope
- In scope: approved Cockpit audit follow-up tasks created from the read-only audit, starting with the foundation/backend bundle.
- Out of scope for this epic task body: implementation details, dashboard redesign, and duplicate cache/SSE invalidation work already completed by #1346.

## Planning Notes
- First bundle is decomposed into TDD-paired child tasks under this parent.
- Child tasks are placed in backlog so the normal pipeline can architecture-review and dispatch them.

## Phase 1 Foundation/Backend Bundle
Tasks created under this epic:
- #1364 P1-01: Test Cockpit PDS v4 build compatibility. No dependencies.
- #1365 P1-02: Fix Cockpit PDS v4 build compatibility. Depends on #1364.
- #1366 P1-03: Test Cockpit PDS runtime loading under CSP. Depends on #1365.
- #1367 P1-04: Fix Cockpit PDS runtime loading under CSP. Depends on #1366.
- #1368 P1-05: Test kanban corruption scanner encoding hardening. No dependencies.
- #1369 P1-06: Harden kanban corruption scanner encoding handling. Depends on #1368.
- #1370 P1-07: Test Cockpit backend error envelope and guidance contract. No dependencies.
- #1371 P1-08: Implement Cockpit backend error envelope and guidance contract. Depends on #1370.
- #1372 P1-09: Test Cockpit health false-OK prevention. Depends on #1367, #1369, and #1371.
- #1373 P1-10: Implement Cockpit health false-OK prevention. Depends on #1372.
- #1374 P1-11: Test Cockpit frontend error-contract adoption. Depends on #1367, #1371, and #1373.
- #1375 P1-12: Implement Cockpit frontend error-contract adoption. Depends on #1374.

Dependency layers:
- Layer 1: #1364, #1368, #1370.
- Layer 2: #1365, #1369, #1371.
- Layer 3: #1366.
- Layer 4: #1367.
- Layer 5: #1372.
- Layer 6: #1373.
- Layer 7: #1374.
- Layer 8: #1375.

Planning constraints:
- All child tasks are in backlog, critical priority, tagged cockpit and audit-remediation.
- Every implementation task depends on its corresponding test task.
- Cache/SSE invalidation work from #1346 is intentionally excluded.
