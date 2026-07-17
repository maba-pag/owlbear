---
approved_at: null
categories: [pitfall, process]
confidence: 0.89
contested_by_task: null
created_at: '2026-05-19T04:23:37.421682Z'
didnt_use_count: 4
id: 05d14bba-d6cb-4a42-80a9-29c2a8079291
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.87
source_agent: reviewer
state: curated
title: Route allowlists need field-level proof across the full proof surface
unremarkable_count: 2
updated_at: '2026-07-17T18:29:41.546067+00:00'
---

When a contract makes multiple fields editable, prove each field is persisted or prove the shared update loop covers all fields. A successful multi-field request can false-green while some inputs are silently dropped.
