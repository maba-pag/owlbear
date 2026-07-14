---
approved_at: null
categories: [process, pitfall]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-28T00:43:03.166007Z'
didnt_use_count: 0
id: 73366e39-a355-4b3b-9fca-400fff7b375c
outstanding_count: 0
scope_agents: [builder, shaper, verifier]
score: 0.0
source_agent: builder
state: deleted
title: Whole-file proof commands can contradict excluded scope
unremarkable_count: 0
updated_at: '2026-07-14T23:57:25.798299+00:00'
---

When an AC requires a whole-file test command while explicitly excluding a failing section in that file, treat the command as a scope/proof-plan contradiction. Record the out-of-scope failure evidence and reject to shape; the shaper narrows the proof target or sequences the prerequisite.
