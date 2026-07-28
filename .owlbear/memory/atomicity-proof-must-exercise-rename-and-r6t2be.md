---
approved_at: null
categories: [pitfall, process]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-17T01:35:51.946837Z'
didnt_use_count: 44
id: 67b38fbb-9690-4ba3-9356-094640e2a479
outstanding_count: 3
scope_agents: [builder, verifier]
score: 1.11
source_agent: copilot
state: curated
title: Atomicity proof must exercise rename and rollback
unremarkable_count: 5
updated_at: '2026-07-28T10:00:19.430277+00:00'
---

Atomic-write proofs must verify observable replacement and rollback behavior. After an injected mid-write failure, the prior content must be preserved or no partial destination left behind; destination existence alone cannot establish atomicity.
