---
approved_at: null
categories: [pitfall, tool-usage, domain-knowledge]
confidence: 0.85
contested_by_task: null
created_at: '2026-05-27T11:32:34.925889Z'
didnt_use_count: 0
id: f28fd5ef-56e5-43a8-8767-b0f8e9cdf078
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: builder
state: deleted
title: MagicMock can misrepresent slotted optional attributes
unremarkable_count: 0
updated_at: '2026-07-14T23:57:25.560858+00:00'
---

When production code must distinguish an unset optional slot from a present attribute, hasattr/getattr can be misleading with MagicMock. Validate the branch against the real slotted lifecycle object; use object.__getattribute__ with AttributeError handling only when absent-versus-present is part of the production contract.
