---
id: 42bb58dc-43ae-42b1-8394-9f6e07fbb44d
title: 'Reviewer: explicit npm test AC overrides default behavioral-scope proof'
categories:
- process
- tool-usage
- pitfall
confidence: 0.87
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-12T20:14:14.436697Z'
updated_at: '2026-05-12T21:24:50.759403Z'
approved_at: null
---

When a frontend task carries `Proof bundle: behavioral` but an AC line explicitly requires `npm test` to pass, do not stop at builder-scoped proof. Verify the package.json test script coverage and use quality-runner for a full frontend test run before verdicting AC sufficiency. Explicit AC commands take precedence over the default proof bundle scope.
