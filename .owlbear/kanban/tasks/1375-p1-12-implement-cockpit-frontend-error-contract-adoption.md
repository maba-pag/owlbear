---
id: 1375
title: 'P1-12: Implement Cockpit frontend error-contract adoption'
status: backlog
priority: critical
created: 2026-05-06T00:58:53.765221+00:00
updated: 2026-05-06T01:01:30.588996+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:fix
- frontend
- interface-contract
- error-handling
parent: 1363
depends_on:
- 1374
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Adopt the Cockpit backend error envelope across frontend API calls and user-visible recoverable error states.

## Problem Evidence
- Hooks and components handle errors inconsistently; some failures become empty state or no-op.
- DetailTab only handles a narrow set of statuses specially.
- Health, decision request, task fetch, mutation, and repair errors are currently inconsistent.

## Acceptance Criteria
- Frontend API calls parse and render the backend error envelope from #1371 consistently.
- Detail, board moves, health scan, decision request polling/resolution, repair, and task fetch flows show user-visible recoverable error states.
- No expected backend error becomes a silent no-op, false empty state, or false health OK.
- Retry or refetch affordances are available where the flow is recoverable.
- The health behavior from #1373 is preserved rather than duplicated or regressed.
- Tests from #1374 pass.

## Scope
- In scope: Cockpit frontend error parsing and recoverable error rendering across existing flows.
- Out of scope: backend contract changes, PDS runtime/build foundation, dashboard redesign, and cache/SSE invalidation from #1346.

## Test Dependency
Satisfies #1374.
