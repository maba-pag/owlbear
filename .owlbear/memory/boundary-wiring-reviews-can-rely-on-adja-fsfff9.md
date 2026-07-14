---
approved_at: null
categories: [process, pitfall]
confidence: 0.85
contested_by_task: null
created_at: '2026-05-27T02:28:25.958049Z'
didnt_use_count: 0
id: 7180b320-f13b-41ad-acb4-f087ce7ce685
outstanding_count: 0
scope_agents: [verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: Boundary wiring reviews can rely on adjacent durable payload proof
unremarkable_count: 0
updated_at: '2026-07-14T22:17:59.089538+00:00'
---

When reviewing thin MCP/boundary wiring tasks, do not fail only because task-local tests assert top-level response keys if the adjacent lower-layer durable suite already proves the nested payload contents and the AC does not explicitly require deeper boundary assertions.
