---
approved_at: null
categories: [pitfall]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T14:28:34.211964Z'
didnt_use_count: 0
id: 4c4906d9-7aad-4a83-9c8a-2a15076f625a
outstanding_count: 0
scope_agents: [verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: Explicit negative AC clauses need direct proof
unremarkable_count: 0
updated_at: '2026-07-14T23:52:41.694040+00:00'
---

In Cockpit frontend reviews, do not accept source-structure inference for explicit negative AC boundaries. If a task says a state resets on different task.id or excludes TaskActions flows, same-id survival tests or clean-form editor clicks are not enough; require a direct failing test for the named branch.
