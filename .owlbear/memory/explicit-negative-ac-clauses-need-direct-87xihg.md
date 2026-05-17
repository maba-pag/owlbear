---
id: 4c4906d9-7aad-4a83-9c8a-2a15076f625a
title: Explicit negative AC clauses need direct proof
categories:
- pitfall
confidence: 0.84
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-17T14:28:34.211964Z'
updated_at: '2026-05-17T17:03:12.457469Z'
approved_at: null
---

In Cockpit frontend reviews, do not accept source-structure inference for explicit negative AC boundaries. If a task says a state resets on different task.id or excludes TaskActions flows, same-id survival tests or clean-form editor clicks are not enough; require a direct failing test for the named branch.
