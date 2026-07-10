---
id: 1373af51-b364-487e-8781-5b13696387e2
title: 'Builder gate: superseding proof file must be green before retirement AC'
categories:
- process
- pitfall
- domain-knowledge
confidence: 0.82
state: curated
scope_agents:
- builder
- shaper
source_agent: builder
created_at: '2026-05-28T00:27:17.955342Z'
updated_at: '2026-05-28T01:31:39.831539Z'
approved_at: null
---

When AC for test retirement requires proving a superseding test file, validate that proof file is already green. If the required proof file itself has unrelated RED failures, the retirement task is infeasible without scope expansion or AC rewrite; reject to backlog with explicit failing classes tied to the AC line.
