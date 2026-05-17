---
id: 67b38fbb-9690-4ba3-9356-094640e2a479
title: Atomicity proof must exercise rename and rollback
categories:
- pitfall
- process
- tool-usage
confidence: 0.86
state: curated
scope_agents:
- reviewer
- test-writer
- builder
source_agent: copilot
created_at: '2026-05-17T01:35:51.946837Z'
updated_at: '2026-05-17T01:48:10.789910Z'
approved_at: null
---

For filesystem or task-write atomicity reviews, target-file existence is not enough. Require an assertion that would fail if a non-atomic write, skipped `replace()`, or missing rollback path were used, such as verifying rename/replace was called or simulating a mid-write failure.
