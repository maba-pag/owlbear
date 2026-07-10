---
id: aeb19bea-86e4-4263-8c22-6b05bba726a3
title: Refetch success flows need visibility proof
categories:
- pitfall
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:37:11.933461Z'
updated_at: '2026-05-17T01:48:20.610724Z'
approved_at: null
---

When a child success flow calls a parent refetch, check whether the parent loading gate unmounts the success/results UI. Require an integration test proving success content remains visible or recovers correctly through the refetch transition.
