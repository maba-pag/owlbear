---
id: 1372
title: 'P1-09: Test Cockpit health false-OK prevention'
status: backlog
priority: critical
created: 2026-05-06T00:58:49.363309+00:00
updated: 2026-05-06T01:00:54.678917+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:test
- frontend
- health
- interface-contract
parent: 1363
depends_on:
- 1367
- 1369
- 1371
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Write frontend regression tests for Cockpit health states so scan failures cannot render as healthy or empty.

## Problem Evidence
- useScanPolling exposes errors, but Shell ignores the error.
- HealthBadge can show Health OK when a scan fails.
- Users need scan failure distinguished from a successful scan with zero issues.

## Acceptance Criteria
- Tests cover scan loading, scan succeeded with zero issues, scan succeeded with issues, and scan failed/error states.
- Tests prove a failed scan never renders as Health OK or No issues.
- Tests prove actionable error text/state is visible and retry or refetch is available.
- Tests consume the backend error envelope from #1371 and scanner behavior from #1369 rather than inventing a route-only workaround.
- The proof fails against the audited false-OK behavior and is suitable for #1373 to satisfy.

## Scope
- In scope: Cockpit frontend health state rendering and retry/refetch behavior.
- Out of scope: backend scanner hardening, backend error-envelope implementation, dashboard redesign, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1373.
