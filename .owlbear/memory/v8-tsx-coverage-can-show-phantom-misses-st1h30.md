---
id: aef43326-a56d-4f2c-85fb-97b82686e9d6
title: V8 TSX coverage can show phantom misses
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.8
state: curated
scope_agents:
- reviewer
- builder
- test-writer
source_agent: copilot
created_at: '2026-05-17T01:39:00.018259Z'
updated_at: '2026-05-17T01:48:32.178455Z'
approved_at: null
---

Vitest V8 coverage for TSX/JSX can report near-threshold misses from compiled `_jsx`/`_jsxs` bytecode positions. Before failing a task on a sub-90% TSX coverage number, check whether lines/functions are fully covered and whether uncovered items map to compiled positions.
