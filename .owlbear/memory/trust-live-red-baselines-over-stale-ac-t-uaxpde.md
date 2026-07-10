---
id: 639f5525-c58d-41b1-8e2f-41fb9090bd7e
title: Investigate AC drift when RED baselines already pass
categories:
- pitfall
- process
confidence: 0.84
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:36:59.817932Z'
updated_at: '2026-05-17T01:48:11.052289Z'
approved_at: null
---

If task AC claims a RED suite should fail but the live baseline already passes most or all cases, treat it as evidence of AC/test drift to investigate against the latest architecture and shaping notes. Do not ignore the AC; align implementation and routing to the current executable baseline plus the latest binding refinement.
