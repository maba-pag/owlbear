---
id: 4939d287-6710-4a71-b77e-0feb6be4174b
title: MCP rename fallout can break durable test imports
categories:
- domain-knowledge
- behaviour
confidence: 0.8
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-27T18:29:38.976933Z'
updated_at: '2026-05-27T19:08:00.468212Z'
approved_at: null
---

When MCP tool functions are renamed, root durable tests may fail during collection from stale imports. Updating imports to new names with local aliases can preserve existing test bodies while restoring collection quickly.
