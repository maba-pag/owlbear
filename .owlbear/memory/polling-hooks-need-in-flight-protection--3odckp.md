---
id: faf1c416-e7ed-4836-b545-341e52bcc809
title: Polling hooks need in-flight protection tests
categories:
- pitfall
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:37:14.519769Z'
updated_at: '2026-05-17T01:48:20.641663Z'
approved_at: null
---

Polling hooks that run async fetches on intervals need explicit in-flight or queued-repoll protection. Instant-resolve interval tests can false-green by missing concurrent polls and stale-response overwrite behavior.
