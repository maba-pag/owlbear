---
approved_at: null
categories: [pitfall, process]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-19T23:42:44.013707Z'
didnt_use_count: 3
id: 30faa49c-088b-4083-9f43-4f97db632720
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.86
source_agent: reviewer
state: curated
title: Separate polling badge counts can stale after mutations
unremarkable_count: 0
updated_at: '2026-07-17T05:06:09.990698+00:00'
---

When a mutation succeeds, any separately polled badge or summary it affects must be proven fresh after the mutation; independent polling can leave the displayed count stale.
