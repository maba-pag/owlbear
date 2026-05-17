---
id: e23a7337-626f-438c-b388-95d1883e7f29
title: Review proof must include named durable suites
categories:
- pitfall
- process
confidence: 0.86
state: approved
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-16T20:30:11.103692Z'
updated_at: '2026-05-16T21:55:14.664941Z'
approved_at: '2026-05-16T21:55:14.664949Z'
---

When a brief or architect guidance names durable suites, do not pass review on task-local tests plus source grep alone. Require proof from the named suites too; stale durable tests can still enforce retired contracts while the task-local suite passes green.
