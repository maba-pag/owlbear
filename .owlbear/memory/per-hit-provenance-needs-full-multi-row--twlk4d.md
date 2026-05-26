---
id: eda7582e-ad48-4c80-85a1-683a12abaf86
title: Per-hit provenance needs full multi-row proof
categories:
- pitfall
- process
confidence: 0.88
state: curated
scope_agents:
- reviewer
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-26T20:57:49.870628Z'
updated_at: '2026-05-26T23:03:00.393613Z'
approved_at: null
---

When an AC says metadata is emitted per hit/row, do not accept a multi-hit test that only proves count plus a subset like IDs or scores. If other fields are only asserted in single-hit tests, later rows can still reuse first-row metadata and false-green.
