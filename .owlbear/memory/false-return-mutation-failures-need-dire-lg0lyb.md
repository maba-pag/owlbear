---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-17T15:43:31.247711Z'
didnt_use_count: 6
id: b0c830a4-8cd0-4fe9-a0ae-2e98c4825ca4
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.86
source_agent: reviewer
state: curated
title: False-return mutation failures need direct proof
unremarkable_count: 0
updated_at: '2026-07-23T14:35:14.325637+00:00'
---

Cockpit mutation hooks report handled failures by resolving `false`. For a UI that reacts to mutation success, prove the initial `false` result does not show success; rejection-only mocks do not cover this contract.
