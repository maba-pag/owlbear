---
id: a0484b71-4996-4245-9815-f7b4b585b142
title: Ref-stabilized callbacks need stale-ref proof
categories:
- pitfall
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:37:27.122394Z'
updated_at: '2026-05-17T01:48:20.763845Z'
approved_at: null
---

For ref-stabilized callbacks, asserting no extra call on callback identity change does not prove the ref updates to the latest callback. Require a stale-ref test that changes the callback after mount and asserts the new version is invoked.
