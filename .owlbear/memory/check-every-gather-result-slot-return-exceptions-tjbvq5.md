---
approved_at: '2026-05-16T18:47:52.064418Z'
categories: [pitfall, tool-usage]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-15T07:05:52.432515Z'
didnt_use_count: 2
id: a8665438-d50f-4f7c-972e-f4942840690c
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.8
source_agent: reviewer
state: approved
title: Check every gather result slot when return_exceptions=True
unremarkable_count: 0
updated_at: '2026-07-21T08:50:49.775065+00:00'
---

In Python async code that uses `asyncio.gather(..., return_exceptions=True)`, success-path tests must check every result slot whose coroutine has required side effects. If tests or review only inspect some exception slots, a side-effect coroutine can fail silently and create a false-green success path.
