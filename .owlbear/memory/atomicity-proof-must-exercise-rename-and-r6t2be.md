---
approved_at: null
categories:
- pitfall
- process
- tool-usage
confidence: 0.86
created_at: '2026-05-17T01:35:51.946837Z'
id: 67b38fbb-9690-4ba3-9356-094640e2a479
scope_agents:
- verifier
- builder
source_agent: copilot
state: curated
title: Atomicity proof must exercise rename and rollback
updated_at: '2026-05-21T17:43:30.030881+00:00'
---

For filesystem or task-write atomicity reviews, target-file existence is not enough. Require an assertion that would fail if a non-atomic write, skipped `replace()`, or missing rollback path were used, such as verifying rename/replace was called or simulating a mid-write failure.
