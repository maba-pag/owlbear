---
id: dcdf6747-e28e-4c68-88cc-ec53c54e5367
title: Rollback paths need deep snapshots and CAS-safe undo
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.88
state: curated
scope_agents:
- builder
- reviewer
source_agent: copilot
created_at: '2026-05-17T01:35:46.991119Z'
updated_at: '2026-05-17T01:48:10.756159Z'
approved_at: null
---

For mutation rollback paths, snapshot state with deep copies before mutation, reverse archive file moves before rollback writes, and preserve CAS semantics if the forward write used CAS. Plain field-level undo or non-CAS rollback writes can clobber concurrent state.
