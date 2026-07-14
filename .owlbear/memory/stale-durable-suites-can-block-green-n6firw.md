---
approved_at: null
categories: [pitfall, process]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-17T01:35:36.543861Z'
didnt_use_count: 0
id: f15b03f9-eb2d-4996-8058-f86d69a70e5f
outstanding_count: 0
scope_agents: [builder, verifier, shaper]
score: 0.0
source_agent: copilot
state: deleted
title: Stale durable suites can block GREEN
unremarkable_count: 0
updated_at: '2026-07-14T23:38:35.030071+00:00'
---

If durable suites encode contradictory contracts or stale fixtures for the same adapter/function surface, GREEN can be structurally impossible until tests are migrated. Correct stale durable tests before implementation work instead of force-fitting code to incompatible suites.
