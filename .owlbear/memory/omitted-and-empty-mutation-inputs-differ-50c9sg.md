---
id: 77cf7446-0c4e-4060-937b-3f96cbedbe52
title: Omitted and empty mutation inputs differ
categories:
- pitfall
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:36:57.394041Z'
updated_at: '2026-05-17T01:48:11.013527Z'
approved_at: null
---

Mutation APIs can treat omitted fields and empty strings differently; defaulting an omitted parameter to `""` can become a destructive clear path. Trace wrapper defaults through kwargs assembly to persistence before accepting optional mutation behavior.
