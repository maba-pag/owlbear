---
id: fba4ddbe-ab03-45cb-8737-ef4b37f5deba
title: Pydantic model_copy does not revalidate here
categories:
- pitfall
- domain-knowledge
- tool-usage
confidence: 0.8
state: curated
scope_agents:
- builder
- test-writer
- reviewer
source_agent: copilot
created_at: '2026-05-17T01:38:48.141953Z'
updated_at: '2026-05-17T01:48:32.061349Z'
approved_at: null
---

In this workspace's Pydantic v2 version, `BaseModel.model_copy()` does not support `validate=`. For mutation-time revalidation, build the full payload and call `Model.model_validate(payload)`, then map `ValidationError` at the boundary.
