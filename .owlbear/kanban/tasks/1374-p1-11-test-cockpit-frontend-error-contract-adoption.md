---
id: 1374
title: 'P1-11: Test Cockpit frontend error-contract adoption'
status: backlog
priority: critical
created: 2026-05-06T00:58:52.272079+00:00
updated: 2026-05-06T01:01:20.028829+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:test
- frontend
- interface-contract
- error-handling
parent: 1363
depends_on:
- 1367
- 1371
- 1373
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Write frontend tests for consistent Cockpit error-envelope parsing and recoverable error rendering across API flows.

## Problem Evidence
- Hooks and components handle errors inconsistently; some failures become empty state or no-op.
- DetailTab handles 409, 404, and 422 specially but not the broader backend contract.
- Health, decision request, task fetch, mutation, and repair errors are displayed inconsistently.

## Acceptance Criteria
- Tests prove frontend API calls parse the backend error envelope from #1371 consistently.
- Tests cover representative error rendering and retry/refetch paths for detail, board moves, health scan, decision request polling/resolution, repair, and task fetch flows.
- Tests prove no expected backend error becomes a silent no-op or false empty state.
- Tests preserve the health false-OK protection from #1373 while covering the broader contract.
- The proof fails against the audited inconsistent handling and is suitable for #1375 to satisfy.

## Scope
- In scope: Cockpit frontend error parsing and user-visible recoverable error-state tests.
- Out of scope: backend envelope implementation, PDS build/runtime fixes, dashboard redesign, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1375.
