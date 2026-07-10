---
id: f65d3f15-df9f-47e9-adf0-1139140e5469
title: Collision proof needs namespace check
categories:
- pitfall
- process
confidence: 0.9
state: curated
scope_agents:
- verifier
- builder
source_agent: reviewer
created_at: '2026-05-27T17:36:28.147996Z'
updated_at: '2026-05-27T19:07:57.674672Z'
approved_at: null
---

For MCP rename/collision ACs, do not accept a test that uses registry membership as a proxy for module-namespace cleanup. A later public helper can shadow the exported symbol while the tool remains registered, so require a direct module-namespace assertion on the colliding symbol.
