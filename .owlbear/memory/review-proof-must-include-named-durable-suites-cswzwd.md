---
approved_at: '2026-05-16T21:55:14.664949Z'
categories: [pitfall, process]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-16T20:30:11.103692Z'
didnt_use_count: 1
id: e23a7337-626f-438c-b388-95d1883e7f29
outstanding_count: 0
scope_agents: [verifier]
score: 0.85
source_agent: reviewer
state: approved
title: Review proof must include named durable suites
unremarkable_count: 1
updated_at: '2026-07-21T09:06:12.908783+00:00'
---

When a brief or shaper guidance names durable suites, do not pass review on task-local tests plus source grep alone. Require proof from the named suites too; stale durable tests can still enforce retired contracts while the task-local suite passes green.
