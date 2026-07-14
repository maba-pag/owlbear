---
approved_at: null
categories: [pitfall, process]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:38:14.311775Z'
didnt_use_count: 0
id: b8ea1fc3-8851-424c-9ffd-f8307ebbab80
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: TestFromAC assertions carry AC proof
unremarkable_count: 0
updated_at: '2026-07-14T23:51:28.784057+00:00'
---

For TDD task proof, assertions should live in `TestFromAC_*` classes for the mapped ACs. Exploratory `TestBuilderDiscovered` coverage can support diagnosis, but incidental coverage there should not substitute for AC-anchored proof.
