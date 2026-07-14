---
approved_at: null
categories: [tool-usage, env-context]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-27T20:46:53.600484Z'
didnt_use_count: 0
id: 6f72dc3f-ba2a-4c73-929e-d0cb8852c83f
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: builder
state: deleted
title: quality-runner full mode timeout fallback
unremarkable_count: 0
updated_at: '2026-07-14T21:19:21.176886+00:00'
---

For task-level smoke work touching mcp-knowledge server, quality-runner mode=full can time out on tests/ serve/ -m "not api" and auto-fallback to scoped evidence. Plan scoped proof runs (task tests + relevant regression file) as primary evidence and treat full-mode as best-effort.
