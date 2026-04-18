---
id: 938
title: 'P3-02: CI sync — build SPA bundle into main branch'
status: research
priority: important
created: 2026-04-17T19:59:26.740493+00:00
updated: 2026-04-17T19:59:26.740493+00:00
tags:
- cockpit
- docs
- phase-3
- type:build
parent: 920
depends_on:
- 937
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Extend the sync-to-main GitHub Actions workflow to build the SPA bundle so consumer-side users need no Node toolchain (D15).

## Acceptance Criteria

- [ ] GitHub Actions workflow updated: adds step to `npm ci; npm run build` in `serve/cockpit/web/`
- [ ] Built `dist/` directory included in the files synced to main branch
- [ ] Consumer clone of main branch has a working cockpit without Node/npm installed
- [ ] Build failure blocks the sync (no broken or missing bundle shipped to main)
- [ ] `serve/cockpit/web/node_modules/` excluded from sync

## Files

- `.github/workflows/sync-to-main.yml` (updated)