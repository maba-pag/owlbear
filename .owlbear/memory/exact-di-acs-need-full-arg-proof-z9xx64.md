---
approved_at: null
categories: [pitfall, process]
confidence: 0.85
contested_by_task: null
created_at: '2026-05-27T00:23:36.549612Z'
didnt_use_count: 0
id: 3d09b76a-e2ad-46db-ae26-134487e904ff
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: Exact DI ACs need complete wiring proof
unremarkable_count: 0
updated_at: '2026-07-14T23:57:05.093852+00:00'
---

When an AC explicitly names constructor-injected dependencies, proof must verify each named dependency is retained or wired as the contract requires. Checking only a subset of identities can false-green incomplete dependency injection.
