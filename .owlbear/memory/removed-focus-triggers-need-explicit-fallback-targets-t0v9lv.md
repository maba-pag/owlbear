---
approved_at: '2026-05-17T00:13:41.289561Z'
categories: [pitfall, process]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-15T07:16:07.292293Z'
didnt_use_count: 26
id: 99e06211-10c6-44c7-b6e8-9130f12ab9fa
outstanding_count: 0
scope_agents: [verifier, shaper, builder]
score: 0.86
source_agent: reviewer
state: approved
title: Removed focus triggers need explicit fallback targets
unremarkable_count: 0
updated_at: '2026-07-24T13:27:37.297786+00:00'
---

When a modal/dialog opener is removed before close, do not treat ancestor containment as focus-return proof. Architecture must name the explicit fallback target, and tests/review should prove focus returns to that exact replacement element rather than a broader region.
