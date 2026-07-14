---
approved_at: null
categories: [pitfall, process, domain-knowledge]
confidence: 0.88
contested_by_task: null
created_at: '2026-05-17T01:35:46.991119Z'
didnt_use_count: 0
id: dcdf6747-e28e-4c68-88cc-ec53c54e5367
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Rollback paths need deep snapshots and CAS-safe undo
unremarkable_count: 0
updated_at: '2026-07-14T23:38:35.149157+00:00'
---

For mutation rollback paths, snapshot state with deep copies before mutation, reverse archive file moves before rollback writes, and preserve CAS semantics if the forward write used CAS. Plain field-level undo or non-CAS rollback writes can clobber concurrent state.
