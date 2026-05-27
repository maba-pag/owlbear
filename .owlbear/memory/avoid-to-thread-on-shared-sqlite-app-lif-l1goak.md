---
id: 8d9d0ef8-53e2-4c63-bfaa-7f3b012d1bfe
title: Avoid to_thread on shared sqlite app-lifespan connections
categories:
- pitfall
- domain-knowledge
confidence: 0.91
state: curated
scope_agents:
- builder
- reviewer
- architect
source_agent: builder
created_at: '2026-05-27T02:50:52.188618Z'
updated_at: '2026-05-27T02:52:26.733134Z'
approved_at: null
---

In mcp-knowledge, app_lifespan shares one sqlite3 connection with SqliteSourceStore. Calling store.list_sources/register_source via asyncio.to_thread can trigger sqlite cross-thread errors; keep those calls on the request thread unless connection is explicitly thread-safe.
