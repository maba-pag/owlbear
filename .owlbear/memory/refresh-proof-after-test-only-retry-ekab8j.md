---
id: 12ac3155-c13a-41c6-8f41-7c206cb6f6f0
title: Refresh proof after test-only retry
categories:
- process
- pitfall
confidence: 0.84
state: curated
scope_agents:
- verifier
source_agent: reviewer
created_at: '2026-05-26T02:02:38.262713Z'
updated_at: '2026-05-26T05:13:50.380941Z'
approved_at: null
---

When a review-cycle task reaches review after a test-only retry with builder skip and the latest builder quality packet predates the added tests, run a scoped quality-runner rerun before failing for stale evidence if the code is unchanged.
