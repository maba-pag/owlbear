---
id: 6f102a38-851f-477b-8178-0b066bace6b6
title: 'Reviewer: resource-uniqueness ACs need duplicate-firing proof'
categories:
- pitfall
- process
confidence: 0.9
state: curated
scope_agents:
- reviewer
- test-writer
source_agent: memory-curator:file-inbox
created_at: '2026-05-13T04:43:32.257316Z'
updated_at: '2026-05-13T04:43:45.499919Z'
approved_at: null
---

When an AC specifies "only one X may be active at a time" (e.g., retry timer, polling interval, SSE connection), a single boundary test is insufficient. Require a duplicate-firing test: trigger a second instance while the first is still active and assert only one survives. Without this, a double-schedule bug passes all boundary tests.
