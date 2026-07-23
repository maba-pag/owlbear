---
approved_at: '2026-05-15T20:47:49.932351Z'
categories: [pitfall, tool-usage, process]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-14T04:07:39.142313Z'
didnt_use_count: 51
id: 0bc670e2-b261-437a-a281-0947f1037b45
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.86
source_agent: reviewer
state: stale
title: Nested CSS selector extractors can be indentation-sensitive
unremarkable_count: 0
updated_at: '2026-07-23T08:44:17.487474+00:00'
---

Selector extractors that anchor with `(?:^|[\n\r])${selector}` can miss valid nested CSS rules when selectors are indented inside @media blocks. In reviews, treat this as brittleness/false-red risk rather than weak proof if the current selector-scoped assertion still matches the implemented contract; prefer helpers that allow leading whitespace.
