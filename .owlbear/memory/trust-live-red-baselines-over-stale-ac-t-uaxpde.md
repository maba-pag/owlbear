---
approved_at: null
categories: [pitfall, process]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:36:59.817932Z'
didnt_use_count: 0
id: 639f5525-c58d-41b1-8e2f-41fb9090bd7e
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Investigate AC drift when RED baselines already pass
unremarkable_count: 0
updated_at: '2026-07-14T23:41:39.768780+00:00'
---

If task AC claims a RED suite should fail but the live baseline already passes most or all cases, treat it as evidence of AC/test drift to investigate against the latest architecture and shaping notes. Do not ignore the AC; align implementation and routing to the current executable baseline plus the latest binding refinement.
