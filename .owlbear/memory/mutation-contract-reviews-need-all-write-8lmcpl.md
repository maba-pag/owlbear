---
approved_at: null
categories: [pitfall, process]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:36:07.331320Z'
didnt_use_count: 8
id: 450666b1-90ab-466b-ba9e-f544ff713838
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.82
source_agent: copilot
state: curated
title: Mutation-contract reviews need all write paths
unremarkable_count: 2
updated_at: '2026-07-24T15:38:13.779462+00:00'
---

When a mutation contract is changed, identify every production write path that can bypass the shared invariant and cover each relevant path with focused proof; validating only the public facade can miss divergent writes.
