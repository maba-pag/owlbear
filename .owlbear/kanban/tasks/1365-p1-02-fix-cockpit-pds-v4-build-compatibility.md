---
id: 1365
title: 'P1-02: Fix Cockpit PDS v4 build compatibility'
status: backlog
priority: critical
created: 2026-05-06T00:58:31.995607+00:00
updated: 2026-05-06T00:59:41.673757+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:build
- frontend
- design-system
- build
parent: 1363
depends_on:
- 1364
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Resolve Cockpit frontend PDS v4 build and type compatibility blockers.

## Problem Evidence
- serve/cockpit/web npm run build currently fails.
- Observed failures include PDS v4 API/type mismatches for component variants, select/input/textarea events and props, JSX namespace typing, and PendingDR/ResolveModal body typing.
- sync-to-main cannot stage a fresh Cockpit dist until the SPA builds cleanly.

## Acceptance Criteria
- npm run build in serve/cockpit/web passes cleanly.
- PDS v4 component usage and type errors are resolved without test hacks, broad type suppression, or hiding errors from TypeScript.
- PendingDR/ResolveModal body typing is corrected if still failing in this foundation path.
- Changes stay scoped to build and design-system compatibility; the dashboard layout and cache/SSE behavior are not redesigned here.
- The tests and quality gates from #1364 pass.

## Scope
- In scope: Cockpit web TypeScript/build compatibility with the installed PDS version.
- Out of scope: CSP-compatible runtime loading, visual dashboard redesign, and cache/SSE invalidation already completed by #1346.

## Test Dependency
Satisfies #1364.
