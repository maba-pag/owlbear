---
id: 1373
title: 'P1-10: Implement Cockpit health false-OK prevention'
status: backlog
priority: critical
created: 2026-05-06T00:58:50.761743+00:00
updated: 2026-05-06T01:01:07.267236+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:fix
- frontend
- health
- interface-contract
parent: 1363
depends_on:
- 1372
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Implement Cockpit health UI semantics so scan failures are visible and cannot be mistaken for a clean health result.

## Problem Evidence
- useScanPolling exposes errors, but Shell ignores the error.
- HealthBadge can show Health OK when scanning fails.
- Users need failed scans distinguished from successful scans with zero issues.

## Acceptance Criteria
- Cockpit health UI distinguishes scan loading, scan succeeded with zero issues, scan succeeded with issues, and scan failed/error.
- A failed scan never renders as Health OK or No issues.
- Actionable error text/state is shown, with retry or refetch available.
- The frontend consumes the backend error envelope from #1371 and scanner behavior from #1369.
- Runtime/build foundation from #1367 remains green.
- Tests from #1372 pass.

## Scope
- In scope: Cockpit frontend health state behavior and retry/refetch affordance.
- Out of scope: backend scanner changes, backend envelope changes, broad frontend error-contract adoption beyond health, dashboard redesign, and cache/SSE invalidation from #1346.

## Test Dependency
Satisfies #1372.
