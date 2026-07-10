---
id: 389cc75c-976d-4f9f-8671-8ae35602259f
title: Design-system ACs need exact selectors and events
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.86
state: curated
scope_agents:
- shaper
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:36:49.294784Z'
updated_at: '2026-05-17T01:48:10.920527Z'
approved_at: null
---

When an AC targets design-system components, name the exact element/selector, emitted event, and DOM behavior. Generic words like `select` or `control` can produce native-control tests that stay green while the actual component contract is untested.
