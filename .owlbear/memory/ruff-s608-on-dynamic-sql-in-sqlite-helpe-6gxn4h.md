---
id: 721dc4af-f28f-4e67-8fef-60e4647d3132
title: Ruff S608 on dynamic SQL in SQLite helpers
categories:
- pitfall
- tool-usage
confidence: 0.86
state: curated
scope_agents:
- builder
- reviewer
source_agent: builder
created_at: '2026-05-26T04:25:19.307959Z'
updated_at: '2026-05-26T05:13:56.937498Z'
approved_at: null
---

In knowledge store code, building SQL with `.format`/f-strings for `IN (...)` triggered ruff S608 and UP032 even with generated placeholders. Prefer fixed parameterized queries (or looped per-id lookup) to keep lint clean in builder tasks.
