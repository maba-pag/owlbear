---
id: 683b6d06-e61e-4b16-a6a9-18070b295cfe
title: MagicMock can hide slotted-context branch bugs
categories:
- pitfall
- process
confidence: 0.91
state: curated
scope_agents:
- verifier
- builder
- shaper
source_agent: reviewer
created_at: '2026-05-27T11:15:56.295116Z'
updated_at: '2026-05-27T11:54:01.865098Z'
approved_at: null
---

When production code branches on app_ctx.__dict__ but the real context is a slotted dataclass, tests that use MagicMock app contexts can falsely prove a branch that production never takes. In reviews, compare mock context shape to the real lifespan object before trusting control-path coverage.
