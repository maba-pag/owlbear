---
id: 1398
title: 'P3-08: Test Cockpit delivery gate and dist packaging checks'
status: backlog
priority: needed
created: 2026-05-06T01:09:47.053865+00:00
updated: 2026-05-06T01:12:31.689610+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:delivery
- type:test
- frontend
- ci
- packaging
- release
parent: 1363
depends_on:
- 1367
- 1385
- 1389
- 1390
- 1396
- 1397
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write tests or workflow assertions proving Cockpit delivery gates catch frontend build, test, visual, and packaging failures before release sync.

## Problem Evidence
- sync-to-main is currently the first hard frontend build gate and removes serve/cockpit/web from the consumer tree after staging dist.
- npm run build currently fails, so sync cannot produce a fresh working dist.
- MegaLinter does not run npm build, Vitest, or Playwright.
- Release packaging must preserve serve/cockpit/dist after source removal.

## Acceptance Criteria
- Tests or CI assertions prove the Cockpit frontend quality gate runs build, relevant tests, and appropriate lint or visual checks before release sync can surprise-fail.
- Tests or workflow assertions prove sync-to-main verifies serve/cockpit/dist/index.html and packaged assets after building.
- Failure of the frontend build or required frontend checks prevents release sync from being treated as successful.
- Packaging verification covers the consumer-tree shape where serve/cockpit/web is absent but serve/cockpit/dist is present and usable.
- The proof fails against the audited delivery setup where frontend build, Vitest, and Playwright are not part of the release gate and is suitable for #1399 to satisfy.

## Scope
- In scope: delivery-gate tests, workflow assertions, packaging checks, and failure-mode proof for Cockpit dist generation and sync readiness.
- Out of scope: fixing the frontend build itself unless required by #1399, writing consumer/developer docs from #1400, changing Cockpit product behavior, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1399.
