---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.91
contested_by_task: null
created_at: '2026-05-27T02:50:52.188618Z'
didnt_use_count: 0
id: 8d9d0ef8-53e2-4c63-bfaa-7f3b012d1bfe
outstanding_count: 0
scope_agents: [builder, verifier, shaper]
score: 0.0
source_agent: builder
state: deleted
title: Avoid to_thread on shared sqlite app-lifespan connections
unremarkable_count: 0
updated_at: '2026-07-14T22:24:11.089853+00:00'
---

In mcp-knowledge, app_lifespan shares one sqlite3 connection with SqliteSourceStore. Calling store.list_sources/register_source via asyncio.to_thread can trigger sqlite cross-thread errors; keep those calls on the request thread unless connection is explicitly thread-safe.
