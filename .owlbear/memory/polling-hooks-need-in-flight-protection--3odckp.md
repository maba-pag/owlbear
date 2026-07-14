---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:37:14.519769Z'
didnt_use_count: 0
id: faf1c416-e7ed-4836-b545-341e52bcc809
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Polling hooks need in-flight protection tests
unremarkable_count: 0
updated_at: '2026-07-14T23:48:46.188914+00:00'
---

Polling hooks that run async fetches on intervals need explicit in-flight or queued-repoll protection. Instant-resolve interval tests can false-green by missing concurrent polls and stale-response overwrite behavior.
