---
id: 1366
title: 'P1-03: Test Cockpit PDS runtime loading under CSP'
status: backlog
priority: critical
created: 2026-05-06T00:58:33.557890+00:00
updated: 2026-05-06T00:59:52.535183+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:test
- frontend
- design-system
- runtime
- csp
parent: 1363
depends_on:
- 1365
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Write the failing runtime smoke proof that Cockpit loads Porsche Design System components in a CSP-compatible way.

## Problem Evidence
- The built Cockpit dist can load while Porsche Design System custom elements are not defined.
- Runtime currently relies on a Porsche CDN script that is blocked by script-src self.
- A visually usable Cockpit shell requires the intended PDS components to be registered without violating CSP.

## Acceptance Criteria
- Runtime smoke coverage proves required PDS custom elements are defined after the Cockpit shell loads.
- The proof fails if a blocked Porsche CDN script is required for component registration.
- The smoke check verifies the shell renders with intended PDS styling signals, not only a blank or unstyled DOM.
- The proof depends on a clean build from #1365 and is suitable for #1367 to satisfy.

## Scope
- In scope: runtime loading and smoke verification for PDS custom elements and shell styling.
- Out of scope: TypeScript build compatibility already covered by #1364/#1365, dashboard redesign, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1367.
