---
id: a5195099-27dd-423c-ac47-e46fc7fb1405
title: Direct proof for named consumer branch
categories:
- pitfall
- process
confidence: 0.82
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-13T13:23:05.925499Z'
updated_at: '2026-05-13T13:58:41.105775Z'
approved_at: null
---

On tests-only reviews, helper-level coverage plus source inspection is not enough when the AC explicitly names a consumer-level branch. Require at least one falsifiable test at that consumer layer before PASS (e.g. start_work redirect deps, not just helper redirect status).
