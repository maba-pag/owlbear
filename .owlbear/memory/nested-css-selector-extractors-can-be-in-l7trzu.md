---
id: 0bc670e2-b261-437a-a281-0947f1037b45
title: Nested CSS selector extractors can be indentation-sensitive
categories:
- pitfall
- tool-usage
- process
confidence: 0.86
state: approved
scope_agents:
- verifier
- builder
source_agent: reviewer
created_at: '2026-05-14T04:07:39.142313Z'
updated_at: '2026-05-15T20:47:49.932337Z'
approved_at: '2026-05-15T20:47:49.932351Z'
---

Selector extractors that anchor with `(?:^|[\n\r])${selector}` can miss valid nested CSS rules when selectors are indented inside @media blocks. In reviews, treat this as brittleness/false-red risk rather than weak proof if the current selector-scoped assertion still matches the implemented contract; prefer helpers that allow leading whitespace.
