---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:36:57.394041Z'
didnt_use_count: 2
id: 77cf7446-0c4e-4060-937b-3f96cbedbe52
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.84
source_agent: copilot
state: curated
title: Omitted and empty mutation inputs differ
unremarkable_count: 0
updated_at: '2026-07-17T05:06:10.035766+00:00'
---

For optional mutation fields, prove omitted input preserves the stored value and an explicit empty value has its intended clear semantics. Do not collapse absence into a destructive default while forwarding the mutation.
