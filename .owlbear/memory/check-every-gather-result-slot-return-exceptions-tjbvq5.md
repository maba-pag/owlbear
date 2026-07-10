---
id: a8665438-d50f-4f7c-972e-f4942840690c
title: Check every gather result slot when return_exceptions=True
categories:
- pitfall
- tool-usage
confidence: 0.8
state: approved
scope_agents:
- builder
- verifier
source_agent: reviewer
created_at: '2026-05-15T07:05:52.432515Z'
updated_at: '2026-05-16T18:47:52.064407Z'
approved_at: '2026-05-16T18:47:52.064418Z'
---

In Python async code that uses `asyncio.gather(..., return_exceptions=True)`, success-path tests must check every result slot whose coroutine has required side effects. If tests or review only inspect some exception slots, a side-effect coroutine can fail silently and create a false-green success path.
