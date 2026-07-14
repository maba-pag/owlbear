---
approved_at: null
categories: [pitfall, process]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-26T05:49:58.581043Z'
didnt_use_count: 0
id: 90c7870a-bc3e-4899-99b1-5ef993947d7f
outstanding_count: 0
scope_agents: [shaper, builder, verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: Document-scope and index-column ACs need adversarial proof
unremarkable_count: 0
updated_at: '2026-07-14T23:54:52.481491+00:00'
---

For a document-scoped query, seed a second document with contaminating data that would change the requested document's result if filtering leaks. For an index required on a specific column, inspect indexed columns with PRAGMA index_info rather than matching only the index name.
