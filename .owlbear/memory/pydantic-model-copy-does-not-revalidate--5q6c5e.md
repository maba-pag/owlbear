---
approved_at: null
categories: [pitfall, domain-knowledge, tool-usage]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-17T01:38:48.141953Z'
didnt_use_count: 0
id: fba4ddbe-ab03-45cb-8737-ef4b37f5deba
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Pydantic model_copy does not revalidate here
unremarkable_count: 0
updated_at: '2026-07-14T23:52:17.230922+00:00'
---

In this workspace's Pydantic v2 version, `BaseModel.model_copy()` does not support `validate=`. For mutation-time revalidation, build the full payload and call `Model.model_validate(payload)`, then map `ValidationError` at the boundary.
