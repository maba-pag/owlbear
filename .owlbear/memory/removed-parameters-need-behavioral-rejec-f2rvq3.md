---
approved_at: null
categories: [pitfall, process]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:37:57.802164Z'
didnt_use_count: 0
id: 9c4a0fa7-9a4e-4f51-9913-d0427d1207bb
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Removed parameters need behavioral rejection tests
unremarkable_count: 0
updated_at: '2026-07-14T23:51:04.511551+00:00'
---

`inspect.signature()` can look clean while hidden `**kwargs` still accepts removed parameters. For parameter-removal contracts, include a behavioral rejection test that calls the removed parameter and asserts `TypeError` or the intended boundary error.
