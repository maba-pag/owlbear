---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:36:54.664758Z'
didnt_use_count: 0
id: 473a45ac-ef4a-4cea-9262-ca21ce31cf05
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: FastAPI response_model strips undeclared fields
unremarkable_count: 0
updated_at: '2026-07-14T23:41:39.672024+00:00'
---

FastAPI `response_model` filtering silently removes fields not declared on the response model. When adding cockpit-specific fields to an engine envelope, define a response model that extends the engine model instead of relying on raw return data.
