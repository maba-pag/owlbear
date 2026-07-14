---
approved_at: null
categories: [pitfall, process, domain-knowledge]
confidence: 0.93
contested_by_task: null
created_at: '2026-05-26T11:22:57.910182Z'
didnt_use_count: 0
id: 2178318d-fba4-432a-9237-497bdb3fb99d
outstanding_count: 0
scope_agents: [verifier, shaper, builder]
score: 0.0
source_agent: reviewer
state: deleted
title: Exact filter contract vs post-filter heuristic
unremarkable_count: 0
updated_at: '2026-07-14T22:41:04.863947+00:00'
---

When a protocol/AC says a filter is applied, reject implementations that fetch a fixed candidate window and post-filter afterward if that can silently drop valid matches outside the window. Require either exact filtering at the search boundary or an explicitly narrowed contract, plus a regression that proves matching hits survive heavy off-filter candidates.
