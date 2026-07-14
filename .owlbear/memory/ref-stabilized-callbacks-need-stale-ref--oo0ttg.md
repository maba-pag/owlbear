---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:37:27.122394Z'
didnt_use_count: 0
id: a0484b71-4996-4245-9815-f7b4b585b142
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Ref-stabilized callbacks need stale-ref proof
unremarkable_count: 0
updated_at: '2026-07-14T23:46:20.723006+00:00'
---

For ref-stabilized callbacks, asserting no extra call on callback identity change does not prove the ref updates to the latest callback. Require a stale-ref test that changes the callback after mount and asserts the new version is invoked.
