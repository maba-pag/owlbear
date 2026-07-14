---
approved_at: null
categories: [pitfall, process]
confidence: 0.88
contested_by_task: null
created_at: '2026-05-26T01:14:54.346373Z'
didnt_use_count: 0
id: 55cfe399-cec0-4f56-83ea-09e2dfd6c997
outstanding_count: 0
scope_agents: [verifier, builder, shaper]
score: 0.0
source_agent: reviewer
state: deleted
title: Happy-path delete assertions need exact IDs
unremarkable_count: 0
updated_at: '2026-07-14T22:57:22.044757+00:00'
---

Verifier pitfall: ordering-only delete assertions are not enough for REPLACED vector cleanup. If code clears recovery state after delete, tests must assert exact stale IDs passed to delete(ids=...) on the successful path, not just that some delete happened before upsert.
