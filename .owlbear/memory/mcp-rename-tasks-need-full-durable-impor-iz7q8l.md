---
approved_at: null
categories: [domain-knowledge, pitfall]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-27T18:45:10.932505Z'
didnt_use_count: 0
id: 0b0a4530-a54d-49dd-9f14-4b1a14fb544d
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: builder
state: deleted
title: MCP rename tasks need full durable import sweep
unremarkable_count: 0
updated_at: '2026-07-14T21:11:19.232431+00:00'
---

When MCP public symbols are renamed, task-local smoke tests can miss adjacent durable suites that import removed symbols directly. Add/verify a workspace-wide import sweep and include all discovered consumers in collection-proof scope before closing the task.
