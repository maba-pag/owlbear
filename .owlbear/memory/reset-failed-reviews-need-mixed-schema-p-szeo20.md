---
approved_at: null
categories: [pitfall, process]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-27T19:58:22.431434Z'
didnt_use_count: 0
id: c5b046d0-2767-4bd7-9ea8-77c36ab52904
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: reviewer
state: deleted
title: Reset_failed reviews need mixed-schema proof
unremarkable_count: 0
updated_at: '2026-07-14T21:16:52.462335+00:00'
---

For EnrichmentStore.reset_failed reviews, task-local tests that only use ensure_tables() can miss AC-critical branches for source_registry/content_chunks bulk filtering and legacy chunks-table sync. Require explicit fixtures that exercise those optional tables when AC names those behaviors.
