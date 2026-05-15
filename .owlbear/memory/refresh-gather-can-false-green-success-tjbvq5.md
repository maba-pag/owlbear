---
id: a8665438-d50f-4f7c-972e-f4942840690c
title: Gather return_exceptions can hide side-effect coroutine failures
categories:
- pitfall
- domain-knowledge
confidence: 0.8
state: curated
scope_agents:
- reviewer
- builder
- test-writer
source_agent: reviewer
created_at: '2026-05-15T07:05:52.432515Z'
updated_at: '2026-05-15T21:47:16.028682Z'
approved_at: null
---

When using asyncio.gather(..., return_exceptions=True), do not treat overall success as proof that every gathered coroutine succeeded. If one result slot is ignored or only some exception slots are checked, side-effect work can fail silently and success-path ACs can false-green. Require explicit checks for every gathered coroutine whose side effects matter.
