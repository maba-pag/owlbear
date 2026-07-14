---
approved_at: null
categories: [pitfall, process, domain-knowledge]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-25T19:47:04.634270Z'
didnt_use_count: 0
id: 9ca815b3-f861-4784-b26a-34b4e7d936d7
outstanding_count: 0
scope_agents: [shaper, builder, verifier]
score: 0.0
source_agent: reviewer
state: curated
title: mcp-kanban tool changes need surface-contract agreement
unremarkable_count: 0
updated_at: '2026-07-14T23:06:08.913712+00:00'
---

For an intentional mcp-kanban tool addition or removal, update the server.py registration and test_mcp_surface_contract.py EXPECTED_TOOLS snapshot together. The live post-lifespan registry must match the snapshot exactly.
