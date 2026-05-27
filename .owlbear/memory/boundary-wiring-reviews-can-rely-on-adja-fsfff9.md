---
id: 7180b320-f13b-41ad-acb4-f087ce7ce685
title: Boundary wiring reviews can rely on adjacent durable payload proof
categories:
- process
- pitfall
confidence: 0.85
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-27T02:28:25.958049Z'
updated_at: '2026-05-27T02:52:26.677615Z'
approved_at: null
---

When reviewing thin MCP/boundary wiring tasks, do not fail only because task-local tests assert top-level response keys if the adjacent lower-layer durable suite already proves the nested payload contents and the AC does not explicitly require deeper boundary assertions.
