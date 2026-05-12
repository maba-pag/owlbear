---
id: 8f166aaa-f331-4be7-a85e-9c72485085ba
title: 'Reviewer: existing-proof bundle can mask AC/proof contract contradictions'
categories:
- process
- pitfall
confidence: 0.89
state: curated
scope_agents:
- reviewer
- architect
source_agent: reviewer
created_at: '2026-05-12T11:59:17.250049Z'
updated_at: '2026-05-12T13:35:48.540978Z'
approved_at: null
---

If review finds a missing behavior proof but the task AC says existing tests must pass unchanged and proof bundle is `existing`/no new test writing, treat the blocker as AC-proof quality. On retry, route to backlog for architect re-scoping rather than pushing builder/test-writer into a contract they cannot satisfy cleanly.
