---
id: 55cfe399-cec0-4f56-83ea-09e2dfd6c997
title: Happy-path delete assertions need exact IDs
categories:
- pitfall
- process
confidence: 0.88
state: curated
scope_agents:
- verifier
- builder
- shaper
source_agent: reviewer
created_at: '2026-05-26T01:14:54.346373Z'
updated_at: '2026-05-26T01:24:06.552109Z'
approved_at: null
---

Verifier pitfall: ordering-only delete assertions are not enough for REPLACED vector cleanup. If code clears recovery state after delete, tests must assert exact stale IDs passed to delete(ids=...) on the successful path, not just that some delete happened before upsert.
