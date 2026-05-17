---
id: 473a45ac-ef4a-4cea-9262-ca21ce31cf05
title: FastAPI response_model strips undeclared fields
categories:
- pitfall
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- builder
- reviewer
- test-writer
source_agent: copilot
created_at: '2026-05-17T01:36:54.664758Z'
updated_at: '2026-05-17T01:48:10.980751Z'
approved_at: null
---

FastAPI `response_model` filtering silently removes fields not declared on the response model. When adding cockpit-specific fields to an engine envelope, define a response model that extends the engine model instead of relying on raw return data.
