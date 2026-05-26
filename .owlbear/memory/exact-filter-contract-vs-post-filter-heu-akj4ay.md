---
id: 2178318d-fba4-432a-9237-497bdb3fb99d
title: Exact filter contract vs post-filter heuristic
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.93
state: curated
scope_agents:
- reviewer
- architect
- builder
source_agent: reviewer
created_at: '2026-05-26T11:22:57.910182Z'
updated_at: '2026-05-26T11:27:30.096615Z'
approved_at: null
---

When a protocol/AC says a filter is applied, reject implementations that fetch a fixed candidate window and post-filter afterward if that can silently drop valid matches outside the window. Require either exact filtering at the search boundary or an explicitly narrowed contract, plus a regression that proves matching hits survive heavy off-filter candidates.
