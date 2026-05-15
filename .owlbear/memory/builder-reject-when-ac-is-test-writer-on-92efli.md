---
id: be4b474b-a6e5-477b-af0e-871d9aad3371
title: Builder reject when AC is test-writer-only RED spec
categories:
- pitfall
- process
confidence: 0.85
state: curated
scope_agents:
- builder
- architect
- planner
source_agent: builder
created_at: '2026-05-14T21:33:00.237238Z'
updated_at: '2026-05-15T03:02:46.048320Z'
approved_at: null
---

If a claimed in-progress task has AC lines exclusively phrased as test-writer actions (e.g., "Test-writer adds ...") and paired GREEN implementation is in a separate build task, builder should reject to backlog for architect routing clarification rather than forcing source edits.
