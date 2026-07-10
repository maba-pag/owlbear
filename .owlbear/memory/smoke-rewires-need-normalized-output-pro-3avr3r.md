---
id: d2b27234-1dac-49c7-9c68-33040f6864d0
title: Smoke rewires need normalized-output proof
categories:
- pitfall
- process
confidence: 0.88
state: curated
scope_agents:
- verifier
source_agent: reviewer
created_at: '2026-05-25T17:12:29.890371Z'
updated_at: '2026-05-25T20:46:41.174827Z'
approved_at: null
---

For smoke-bundle frontend API rewires, do not accept a task-local test that only proves the new endpoint/path if adjacent consumers depend on normalized output. If durable tests on the touched hook or modal still encode the retired API contract, treat that as a blocking test-gap and send the task back to shape.
