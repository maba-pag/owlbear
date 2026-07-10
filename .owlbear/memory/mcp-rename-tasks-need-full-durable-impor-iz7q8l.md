---
id: 0b0a4530-a54d-49dd-9f14-4b1a14fb544d
title: MCP rename tasks need full durable import sweep
categories:
- domain-knowledge
- pitfall
confidence: 0.8
state: curated
scope_agents:
- builder
- verifier
source_agent: builder
created_at: '2026-05-27T18:45:10.932505Z'
updated_at: '2026-05-27T19:08:03.839337Z'
approved_at: null
---

When MCP public symbols are renamed, task-local smoke tests can miss adjacent durable suites that import removed symbols directly. Add/verify a workspace-wide import sweep and include all discovered consumers in collection-proof scope before closing the task.
