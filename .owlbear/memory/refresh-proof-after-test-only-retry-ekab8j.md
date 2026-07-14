---
approved_at: null
categories: [process, pitfall]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-26T02:02:38.262713Z'
didnt_use_count: 0
id: 12ac3155-c13a-41c6-8f41-7c206cb6f6f0
outstanding_count: 0
scope_agents: [verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: Refresh proof after test-only retry
unremarkable_count: 0
updated_at: '2026-07-14T22:53:39.416627+00:00'
---

When a review-cycle task reaches review after a test-only retry with builder skip and the latest builder quality packet predates the added tests, run a scoped quality-runner rerun before failing for stale evidence if the code is unchanged.
