---
approved_at: null
categories: [domain-knowledge, behaviour]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-27T18:29:38.976933Z'
didnt_use_count: 0
id: 4939d287-6710-4a71-b77e-0feb6be4174b
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: MCP rename fallout can break durable test imports
unremarkable_count: 0
updated_at: '2026-07-14T22:17:58.979307+00:00'
---

When MCP tool functions are renamed, root durable tests may fail during collection from stale imports. Updating imports to new names with local aliases can preserve existing test bodies while restoring collection quickly.
