---
id: c5b046d0-2767-4bd7-9ea8-77c36ab52904
title: Reset_failed reviews need mixed-schema proof
categories:
- pitfall
- process
confidence: 0.82
state: curated
scope_agents:
- reviewer
- test-writer
source_agent: reviewer
created_at: '2026-05-27T19:58:22.431434Z'
updated_at: '2026-05-27T22:49:33.273342Z'
approved_at: null
---

For EnrichmentStore.reset_failed reviews, task-local tests that only use ensure_tables() can miss AC-critical branches for source_registry/content_chunks bulk filtering and legacy chunks-table sync. Require explicit fixtures that exercise those optional tables when AC names those behaviors.
