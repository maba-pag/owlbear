---
id: 58409d8d-5fe0-4193-968f-3323044d15de
title: Pydantic extra-forbid needs explicit legacy stripping
categories:
- pitfall
- domain-knowledge
confidence: 0.8
state: curated
scope_agents:
- builder
- test-writer
- reviewer
source_agent: copilot
created_at: '2026-05-17T01:38:50.923607Z'
updated_at: '2026-05-17T01:48:32.091170Z'
approved_at: null
---

When a Pydantic model uses `extra="forbid"` but must silently drop one legacy field, use a `model_validator(mode="before")` to remove that key. Switching to `extra="ignore"` accepts all unknown fields and weakens the contract.
