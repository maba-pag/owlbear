---
id: 7ddc485e-83a1-427c-8b1f-fcabff0350d5
title: Transport-state ACs need negative proof
categories:
- pitfall
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:37:20.219460Z'
updated_at: '2026-05-17T01:48:20.703519Z'
approved_at: null
---

For frontend ACs that qualify a trigger by transport state, include a test that fires the trigger while the guard state is false and asserts suppression. Positive-state simulations alone can hide missing downstream guard checks.
