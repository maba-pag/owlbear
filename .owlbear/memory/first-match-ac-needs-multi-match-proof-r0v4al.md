---
id: 3c983843-0fa3-4599-a322-54f5303cc782
title: First-match AC needs multi-match proof
categories:
- process
- pitfall
confidence: 0.91
state: curated
scope_agents:
- reviewer
- test-writer
source_agent: reviewer
created_at: '2026-05-12T21:37:38.146872Z'
updated_at: '2026-05-12T22:17:41.454895Z'
approved_at: null
---

If an AC says code uses the first regex/selector match, a single matching-input test is insufficient even when the implementation uses Array.find. Require a multi-match test that would fail if a later match were chosen.
