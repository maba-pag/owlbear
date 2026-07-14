---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:37:20.219460Z'
didnt_use_count: 0
id: 7ddc485e-83a1-427c-8b1f-fcabff0350d5
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Transport-state ACs need negative proof
unremarkable_count: 0
updated_at: '2026-07-14T23:50:08.102029+00:00'
---

For frontend ACs that qualify a trigger by transport state, include a test that fires the trigger while the guard state is false and asserts suppression. Positive-state simulations alone can hide missing downstream guard checks.
