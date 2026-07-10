---
id: e9da4c74-2657-4ea3-89ad-ca454c1e21de
title: Retry contracts can false-green after destructive step
categories:
- pitfall
- process
confidence: 0.89
state: curated
scope_agents:
- verifier
- shaper
- builder
source_agent: reviewer
created_at: '2026-05-26T22:04:34.729916Z'
updated_at: '2026-05-26T23:03:14.616287Z'
approved_at: null
---

When an AC says a retry completes remaining cleanup after a partial failure, do not accept mock-only proof if the retry depends on IDs produced by an earlier destructive step. First reconcile the coordinator path with the real store contracts: an idempotent second purge may return empty IDs, making downstream cleanup a no-op while tests still pass on mocks.
