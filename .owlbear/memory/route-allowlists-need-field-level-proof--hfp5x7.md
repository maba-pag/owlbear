---
approved_at: null
categories: [pitfall, process]
confidence: 0.89
contested_by_task: null
created_at: '2026-05-19T04:23:37.421682Z'
didnt_use_count: 0
id: 05d14bba-d6cb-4a42-80a9-29c2a8079291
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: reviewer
state: curated
title: Route allowlists need field-level proof across the full proof surface
unremarkable_count: 0
updated_at: '2026-07-14T23:54:21.890822+00:00'
---

When a contract makes multiple fields editable, prove each field is persisted or prove the shared update loop covers all fields. A successful multi-field request can false-green while some inputs are silently dropped.
