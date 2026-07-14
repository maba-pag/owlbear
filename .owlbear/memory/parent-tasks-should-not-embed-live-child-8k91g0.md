---
approved_at: null
categories: [pitfall, process]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-17T01:38:45.440853Z'
didnt_use_count: 0
id: 69436af9-6d13-4758-ab5a-af66385f17cb
outstanding_count: 0
scope_agents: [planner, verifier, collector]
score: 0.8099999999999999
source_agent: copilot
state: deleted
title: Parent tasks should not embed live child status
unremarkable_count: 1
updated_at: '2026-07-14T17:36:03.297225+00:00'
---

Parent or roll-up tasks should avoid live child-status claims that go stale as children move. Use creation-time snapshots or omit status prose; verifiers and dispatchers should query the board directly for current child state.
