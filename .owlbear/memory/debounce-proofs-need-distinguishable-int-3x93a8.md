---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-17T01:37:29.804847Z'
didnt_use_count: 0
id: 9c40e860-5080-4fe4-86cc-7c590b085b92
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Debounce proofs need distinguishable intermediate states
unremarkable_count: 0
updated_at: '2026-07-14T23:46:20.804706+00:00'
---

Debounce reset tests should use successive inputs that produce different intermediate counts or states, and should capture the stale-timer boundary before the debounce window closes. Same-count inputs can hide an early stale timer firing.
