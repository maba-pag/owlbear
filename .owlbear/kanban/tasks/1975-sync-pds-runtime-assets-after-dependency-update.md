---
id: 1975
title: Sync PDS runtime assets after dependency update
status: collect
priority: high
created: 2026-07-21T17:51:32.013732+02:00
updated: 2026-07-21T18:00:45.503155+02:00
tags:
  - baseline-repair
  - frontend
  - generated-assets
  - scope:cockpit
parent:
depends_on: []
ac:
  - Given the lock-resolved Porsche Design System npm package, `npm run 
    sync:pds` leaves the checked-in core component bundle at that package 
    version and leaves no stale prior-version core bundle.
  - Given the synchronized runtime assets, `npm run build` exits zero and its 
    output contains no `PDS version mismatch` diagnostic.
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Restore the exact admission baseline after the lockfile update resolved Porsche Design System 4.5.0 while checked-in Cockpit runtime assets remained at 4.4.0.

## Scope
Run the existing asset synchronization workflow and commit only its generated runtime-asset replacement plus this task record. Do not change application behavior, package constraints, or unrelated dependencies.

Proof guidance: run the production Cockpit build and the focused PDS/Vite contract tests; the build output must not report a PDS asset/npm version mismatch.

[[2026-07-21T17:58:01+02:00]]
## Builder Notes
- Replaced the 60 checked-in Porsche Design System 4.4.0 component bundles with the 60 bundles generated from the lock-resolved 4.5.0 package by the existing `sync:pds` workflow.
- Inventory proof: core bundle is `porsche-design-system.v4.5.0.e9ec1eb3efc438fd4e3d.js`; stale 4.4.0 core bundle count is zero.
- `npm run build` passed without a PDS version-mismatch diagnostic; only the existing chunk-size warning remains.
- Focused proof passed: Vite PDS contract 9/9 and Python PDS build compatibility 11/11.
- Builder challenger decision: pass; generated diff and unrelated dirty paths were scoped correctly.

[[2026-07-21T18:00:45+02:00]]
## Verify Notes
- Verified builder commit `ae437a2e475c851b5225660234372a46eff6185e` in a clean detached checkout.
- Rerunning `sync:pds` was idempotent and left the checkout clean; the core bundle is PDS 4.5.0 with no stale 4.4.0 core bundle.
- Exact production build passed and an explicit output guard confirmed the version-mismatch diagnostic was absent.
- Maintained contracts passed: Python PDS build compatibility 11/11 and Vite PDS version handling 9/9.
- Verifier challenger decision: pass; no scope drift or unresolved acceptance criterion.
