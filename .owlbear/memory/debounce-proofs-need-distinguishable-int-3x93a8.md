---
id: 9c40e860-5080-4fe4-86cc-7c590b085b92
title: Debounce proofs need distinguishable intermediate states
categories:
- pitfall
- domain-knowledge
confidence: 0.82
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:37:29.804847Z'
updated_at: '2026-05-17T01:48:20.795893Z'
approved_at: null
---

Debounce reset tests should use successive inputs that produce different intermediate counts or states, and should capture the stale-timer boundary before the debounce window closes. Same-count inputs can hide an early stale timer firing.
