---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-17T01:38:50.923607Z'
didnt_use_count: 0
id: 58409d8d-5fe0-4193-968f-3323044d15de
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Pydantic extra-forbid needs explicit legacy stripping
unremarkable_count: 0
updated_at: '2026-07-14T23:52:17.343092+00:00'
---

When a Pydantic model uses `extra="forbid"` but must silently drop one legacy field, use a `model_validator(mode="before")` to remove that key. Switching to `extra="ignore"` accepts all unknown fields and weakens the contract.
