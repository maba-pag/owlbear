---
id: be4b474b-a6e5-477b-af0e-871d9aad3371
title: Builder should reject test-writer-only RED tasks for routing clarification
categories:
- pitfall
- process
confidence: 0.85
state: deleted
scope_agents:
- builder
- architect
- planner
source_agent: builder
created_at: '2026-05-14T21:33:00.237238Z'
updated_at: '2026-05-16T03:59:24.036623Z'
approved_at: null
---

If an in-progress task’s AC is written entirely as test-writer RED work and the paired GREEN implementation lives in a separate build task, builder should reject for architect routing clarification rather than forcing source edits.
