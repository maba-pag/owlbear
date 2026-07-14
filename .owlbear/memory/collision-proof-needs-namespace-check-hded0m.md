---
approved_at: null
categories: [pitfall, process]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-27T17:36:28.147996Z'
didnt_use_count: 0
id: f65d3f15-df9f-47e9-adf0-1139140e5469
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: reviewer
state: deleted
title: Collision proof needs namespace check
unremarkable_count: 0
updated_at: '2026-07-14T22:08:14.669081+00:00'
---

For MCP rename/collision ACs, do not accept a test that uses registry membership as a proxy for module-namespace cleanup. A later public helper can shadow the exported symbol while the tool remains registered, so require a direct module-namespace assertion on the colliding symbol.
