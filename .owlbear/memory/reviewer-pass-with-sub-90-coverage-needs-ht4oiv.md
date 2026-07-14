---
approved_at: null
categories: [process, pitfall]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-26T02:27:35.112164Z'
didnt_use_count: 0
id: 4244ebc6-8d03-4fc6-b1dd-7c4833652418
outstanding_count: 0
scope_agents: [verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: Verifier PASS with sub-90 coverage needs explicit rationale
unremarkable_count: 0
updated_at: '2026-07-14T22:53:39.280962+00:00'
---

When PASSing a behavioral review with module coverage below the general 90% target, do not treat the percentage as implicitly green. State why AC-specific proof is still sufficient and why the lower number is non-blocking, or verifier-challenger review will flag evidence-quality drift.
