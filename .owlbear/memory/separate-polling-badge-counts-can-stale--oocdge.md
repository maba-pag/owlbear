---
id: 30faa49c-088b-4083-9f43-4f97db632720
title: Separate polling badge counts can stale after mutations
categories:
- pitfall
- domain-knowledge
confidence: 0.86
state: curated
scope_agents:
- reviewer
- builder
- test-writer
source_agent: reviewer
created_at: '2026-05-19T23:42:44.013707Z'
updated_at: '2026-05-20T09:00:53.386788Z'
approved_at: null
---

When a UI badge count is sourced from a separate polling hook instead of shared mutation state, do not accept initial-render badge proof alone. Require post-mutation freshness proof, or pending delete / pending->curated edits can leave the badge stale until the next poll.
