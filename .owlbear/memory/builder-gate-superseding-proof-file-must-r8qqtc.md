---
approved_at: null
categories: [process, pitfall, domain-knowledge]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-28T00:27:17.955342Z'
didnt_use_count: 0
id: 1373af51-b364-487e-8781-5b13696387e2
outstanding_count: 0
scope_agents: [builder, shaper]
score: 0.0
source_agent: builder
state: deleted
title: 'Builder gate: superseding proof file must be green before retirement AC'
unremarkable_count: 0
updated_at: '2026-07-14T21:14:16.806459+00:00'
---

When AC for test retirement requires proving a superseding test file, validate that proof file is already green. If the required proof file itself has unrelated RED failures, the retirement task is infeasible without scope expansion or AC rewrite; reject to backlog with explicit failing classes tied to the AC line.
