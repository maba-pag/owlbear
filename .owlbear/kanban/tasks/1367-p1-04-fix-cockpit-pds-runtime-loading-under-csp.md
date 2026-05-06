---
id: 1367
title: 'P1-04: Fix Cockpit PDS runtime loading under CSP'
status: backlog
priority: critical
created: 2026-05-06T00:58:35.956282+00:00
updated: 2026-05-06T01:00:02.638853+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:build
- frontend
- design-system
- runtime
- csp
parent: 1363
depends_on:
- 1366
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Make Cockpit load Porsche Design System custom elements at runtime without requiring a CSP-blocked CDN script.

## Problem Evidence
- The built dist loads but PDS custom elements are not defined.
- The current runtime path is incompatible with script-src self when it depends on the Porsche CDN script.
- A successful sync-to-main needs both a clean build and a runtime that works from the packaged product.

## Acceptance Criteria
- PDS components are loaded locally or otherwise in a CSP-compatible way; no blocked Porsche CDN script is required at runtime.
- Runtime smoke proof confirms required custom elements are defined and the Cockpit shell renders with intended PDS styling.
- The solution works from the built dist used by sync-to-main delivery.
- Changes remain scoped to design-system runtime loading; dashboard redesign and cache/SSE invalidation from #1346 stay out of scope.
- The tests and smoke proof from #1366 pass.

## Scope
- In scope: Cockpit web runtime asset/loading behavior for PDS custom elements.
- Out of scope: broad visual redesign, unrelated router or API behavior, and SSE/cache invalidation.

## Test Dependency
Satisfies #1366.
