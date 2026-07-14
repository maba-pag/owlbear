---
approved_at: null
categories: [pitfall, process, domain-knowledge]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:38:19.471793Z'
didnt_use_count: 0
id: ce81800b-9d4f-4216-8547-479ccdd57228
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Timer-clearing tests need pending-timer preconditions
unremarkable_count: 0
updated_at: '2026-07-14T23:51:52.924283+00:00'
---

For ACs requiring timers to clear on disable or unmount, first assert the timer is actually pending before the disable/unmount action. Clearing from an idle baseline proves nothing and can false-green.
