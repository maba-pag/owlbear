---
id: b0c830a4-8cd0-4fe9-a0ae-2e98c4825ca4
title: False-return mutation failures need direct proof
categories:
- pitfall
- domain-knowledge
confidence: 0.86
state: curated
scope_agents:
- verifier
- builder
source_agent: reviewer
created_at: '2026-05-17T15:43:31.247711Z'
updated_at: '2026-05-17T17:03:17.111259Z'
approved_at: null
---

In Cockpit save-confirmed flows, handled mutation failures resolve false rather than reject. Require at least one task-local test for the initial false-return path; rejection-based mocks or only clear-after-prior-success tests can false-green AC coverage.
