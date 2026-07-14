---
approved_at: null
categories: [pitfall, tool-usage]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-26T04:25:19.307959Z'
didnt_use_count: 0
id: 721dc4af-f28f-4e67-8fef-60e4647d3132
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: builder
state: deleted
title: Ruff S608 on dynamic SQL in SQLite helpers
unremarkable_count: 0
updated_at: '2026-07-14T22:50:28.462685+00:00'
---

In knowledge store code, building SQL with `.format`/f-strings for `IN (...)` triggered ruff S608 and UP032 even with generated placeholders. Prefer fixed parameterized queries (or looped per-id lookup) to keep lint clean in builder tasks.
