---
id: 1512
title: 'Cockpit: Add PDS asset version check to build'
status: research
priority: nice-to-have
created: 2026-05-12T15:49:55.128056+00:00
updated: 2026-05-12T15:50:49.366577+00:00
tags:
  - cockpit
  - frontend
  - cleanup
parent: 1495
depends_on:
  - 1511
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Research: see `.owlbear/research/1510-pds-asset-sync.md` (task #1510).

After PDS assets are synced locally via the sync script (#1511), add a guard that catches version drift between `public/porsche-design-system/` and the npm package.

## Acceptance Criteria

- [ ] Build-time check (Vite plugin or prebuild script) compares core chunk version in `public/porsche-design-system/components/` with PDS npm package version from `node_modules`
- [ ] Version mismatch produces a non-blocking console warning (does not fail the build)
- [ ] Check runs automatically during `npm run build` and `npm run dev`