---
id: 9c4a0fa7-9a4e-4f51-9913-d0427d1207bb
title: Removed parameters need behavioral rejection tests
categories:
- pitfall
- process
confidence: 0.84
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:37:57.802164Z'
updated_at: '2026-05-17T01:48:31.572784Z'
approved_at: null
---

`inspect.signature()` can look clean while hidden `**kwargs` still accepts removed parameters. For parameter-removal contracts, include a behavioral rejection test that calls the removed parameter and asserts `TypeError` or the intended boundary error.
