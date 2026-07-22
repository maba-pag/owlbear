---
approved_at: null
categories: [pitfall, process]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:36:07.331320Z'
didnt_use_count: 4
id: 450666b1-90ab-466b-ba9e-f544ff713838
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.83
source_agent: copilot
state: curated
title: Mutation-contract reviews need all write paths
unremarkable_count: 1
updated_at: '2026-07-22T04:05:46.777867+00:00'
---

When a mutation contract is changed, identify every production write path that can bypass the shared invariant and cover each relevant path with focused proof; validating only the public facade can miss divergent writes.
