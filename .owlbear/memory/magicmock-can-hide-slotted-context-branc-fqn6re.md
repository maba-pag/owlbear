---
approved_at: null
categories: [pitfall, process]
confidence: 0.91
contested_by_task: null
created_at: '2026-05-27T11:15:56.295116Z'
didnt_use_count: 0
id: 683b6d06-e61e-4b16-a6a9-18070b295cfe
outstanding_count: 0
scope_agents: [verifier, builder, shaper]
score: 0.0
source_agent: reviewer
state: deleted
title: MagicMock can hide slotted-context branch bugs
unremarkable_count: 0
updated_at: '2026-07-14T22:16:01.073452+00:00'
---

When production code branches on app_ctx.__dict__ but the real context is a slotted dataclass, tests that use MagicMock app contexts can falsely prove a branch that production never takes. In reviews, compare mock context shape to the real lifespan object before trusting control-path coverage.
