---
id: b8ea1fc3-8851-424c-9ffd-f8307ebbab80
title: TestFromAC assertions carry AC proof
categories:
- pitfall
- process
confidence: 0.84
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:38:14.311775Z'
updated_at: '2026-05-17T01:48:31.832308Z'
approved_at: null
---

For TDD task proof, assertions should live in `TestFromAC_*` classes for the mapped ACs. Exploratory `TestBuilderDiscovered` coverage can support diagnosis, but incidental coverage there should not substitute for AC-anchored proof.
