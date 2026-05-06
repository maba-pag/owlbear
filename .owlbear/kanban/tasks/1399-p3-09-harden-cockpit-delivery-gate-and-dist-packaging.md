---
id: 1399
title: 'P3-09: Harden Cockpit delivery gate and dist packaging'
status: backlog
priority: needed
created: 2026-05-06T01:09:48.720545+00:00
updated: 2026-05-06T01:12:33.500875+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:delivery
- type:build
- frontend
- ci
- packaging
- release
parent: 1363
depends_on:
- 1398
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Harden Cockpit delivery so frontend build, tests, visual checks, and dist packaging are verified before sync-to-main can fail late.

## Problem Evidence
- sync-to-main currently discovers Cockpit frontend build failures only during release sync.
- The consumer tree removes serve/cockpit/web after staging dist, so packaged assets must be verified explicitly.
- MegaLinter does not currently run npm build, Vitest, or Playwright for Cockpit.
- Existing documentation and release flow do not make frontend quality checks a first-class gate.

## Acceptance Criteria
- Cockpit frontend quality gate runs build, relevant tests, and appropriate lint or visual checks before release sync can surprise-fail.
- sync-to-main continues to build Cockpit dist and verifies serve/cockpit/dist/index.html plus packaged assets after the build.
- Release packaging preserves the intended consumer shape: prebuilt dist is present and source web package is not required for consumers.
- Frontend build or required frontend check failures stop the delivery gate clearly and early.
- Verification from #1398 passes without removing valid Cockpit packaging behavior.

## Scope
- In scope: CI or workflow hardening, release-sync packaging checks, frontend quality gate wiring, and delivery verification needed to satisfy #1398.
- Out of scope: consumer/developer docs from #1400, product UI changes, DR lifecycle implementation from #1385, product-boundary guardrails from #1390, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1398.
