---
approved_at: null
categories: [pitfall, tool-usage, domain-knowledge]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-17T01:39:00.018259Z'
didnt_use_count: 0
id: aef43326-a56d-4f2c-85fb-97b82686e9d6
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: copilot
state: deleted
title: V8 TSX coverage can show phantom misses
unremarkable_count: 0
updated_at: '2026-07-14T23:52:17.603957+00:00'
---

Vitest V8 coverage for TSX/JSX can report near-threshold misses from compiled `_jsx`/`_jsxs` bytecode positions. Before failing a task on a sub-90% TSX coverage number, check whether lines/functions are fully covered and whether uncovered items map to compiled positions.
