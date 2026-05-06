---
id: 1371
title: 'P1-08: Implement Cockpit backend error envelope and guidance contract'
status: backlog
priority: critical
created: 2026-05-06T00:58:43.072416+00:00
updated: 2026-05-06T01:00:43.774889+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-api
- type:fix
- backend
- interface-contract
- guidance
parent: 1363
depends_on:
- 1370
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Implement a consistent Cockpit backend error envelope and explicit kanban guidance policy for expected API failures.

## Problem Evidence
- Mutation routes mostly return plain HTTPException detail strings, while kanban errors expose code and user_message.
- CockpitView clears guidance implicitly; the list route passes guidance on cache miss but drops it on cache hit.
- Frontend consumers cannot reliably distinguish expected failures from empty or successful states.

## Acceptance Criteria
- Cockpit expected errors use a stable envelope with code and user-facing message fields; field detail support is included only if it is needed by real callers.
- Mutation, read, admin, decision, scan, and repair routes use the envelope consistently for stale/conflict, validation, not found, invalid config, scanner failure, and repair failure cases.
- The kanban/MCP guidance policy is explicit: each guidance source is intentionally suppressed, transformed, or shown to users.
- Correct HTTP status codes are preserved.
- Backend tests from #1370 pass.
- Frontend UI redesign is not part of this task; frontend adoption is handled later.

## Scope
- In scope: Cockpit backend API error and guidance contract for expected failures.
- Out of scope: frontend rendering changes, broad UI redesign, and cache/SSE invalidation from #1346.

## Test Dependency
Satisfies #1370.
