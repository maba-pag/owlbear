---
id: ce81800b-9d4f-4216-8547-479ccdd57228
title: Timer-clearing tests need pending-timer preconditions
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:38:19.471793Z'
updated_at: '2026-05-17T01:48:31.890033Z'
approved_at: null
---

For ACs requiring timers to clear on disable or unmount, first assert the timer is actually pending before the disable/unmount action. Clearing from an idle baseline proves nothing and can false-green.
