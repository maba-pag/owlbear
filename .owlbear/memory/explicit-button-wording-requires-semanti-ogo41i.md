---
id: 3118bc51-82d5-487f-8d81-c7bdb8d3d20a
title: Explicit button wording requires semantic proof
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.9
state: approved
scope_agents:
- reviewer
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-13T22:33:55.985819Z'
updated_at: '2026-05-15T20:39:57.462405Z'
approved_at: '2026-05-15T20:39:57.462414Z'
---

When a frontend AC says a control is a button, a test that only selects by data-testid and checks ARIA attrs is still insufficient. Require a falsifiable button/role assertion, especially when builder guidance points to an existing <button> pattern; otherwise a div/span with the same attrs can false-green.
