---
id: 1364
title: 'P1-01: Test Cockpit PDS v4 build compatibility'
status: backlog
priority: critical
created: 2026-05-06T00:58:30.519362+00:00
updated: 2026-05-06T00:59:31.448923+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:test
- frontend
- design-system
- build
parent: 1363
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Write the failing test and quality-gate proof for Cockpit PDS v4 build compatibility.

## Problem Evidence
- The Cockpit frontend build currently fails.
- PDS v4 API and type mismatches were observed around tertiary variants, select/input/textarea events and props, JSX namespace typing, and PendingDR/ResolveModal body typing.
- The sync-to-main workflow builds the Cockpit SPA before staging dist, so this blocks delivery.

## Acceptance Criteria
- A focused frontend verification path proves that npm run build in serve/cockpit/web must pass cleanly.
- Coverage or type-focused assertions catch the known PDS v4 component usage failures without broad type suppression.
- The PendingDR and ResolveModal body type mismatch is represented in the failing proof if it is still present.
- The proof fails against the audited broken state and is suitable for #1365 to satisfy.

## Scope
- In scope: Cockpit web build/type verification and PDS v4 compatibility proof.
- Out of scope: runtime custom-element loading, CSP policy changes, dashboard redesign, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1365.
