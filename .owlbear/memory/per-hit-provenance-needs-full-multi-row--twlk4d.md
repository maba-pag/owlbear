---
approved_at: null
categories: [pitfall, process]
confidence: 0.88
contested_by_task: null
created_at: '2026-05-26T20:57:49.870628Z'
didnt_use_count: 0
id: eda7582e-ad48-4c80-85a1-683a12abaf86
outstanding_count: 0
scope_agents: [verifier, builder, shaper]
score: 0.0
source_agent: reviewer
state: deleted
title: Per-hit provenance needs full multi-row proof
unremarkable_count: 0
updated_at: '2026-07-14T22:44:27.563987+00:00'
---

When an AC says metadata is emitted per hit/row, do not accept a multi-hit test that only proves count plus a subset like IDs or scores. If other fields are only asserted in single-hit tests, later rows can still reuse first-row metadata and false-green.
