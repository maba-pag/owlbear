---
id: 69436af9-6d13-4758-ab5a-af66385f17cb
title: Parent tasks should not embed live child status
categories:
- pitfall
- process
confidence: 0.82
state: curated
scope_agents:
- planner
- reviewer
- auditor
source_agent: copilot
created_at: '2026-05-17T01:38:45.440853Z'
updated_at: '2026-05-17T01:48:32.032606Z'
approved_at: null
---

Parent or roll-up tasks should avoid live child-status claims that go stale as children move. Use creation-time snapshots or omit status prose; reviewers and dispatchers should query the board directly for current child state.
