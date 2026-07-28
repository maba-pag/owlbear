---
approved_at: '2026-05-17T03:13:27.704415Z'
categories: [pitfall, tool-usage, domain-knowledge]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-17T01:34:35.497571Z'
didnt_use_count: 51
id: 9b49127d-8575-493a-9d4b-b542ab867d57
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.9
source_agent: copilot
state: stale
title: Playwright route handlers are LIFO
unremarkable_count: 0
updated_at: '2026-07-28T02:12:25.399154+00:00'
---

Playwright `page.route()` handlers are matched last-in-first-out. Register broad catch-all routes such as `/api/**` before registering specific stubs, or the catch-all can override the specific route and make the app receive empty or wrong API responses.
