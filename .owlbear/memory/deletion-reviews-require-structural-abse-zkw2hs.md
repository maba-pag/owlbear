---
id: 5d25d9b0-6f22-4108-be32-7ae6f6c3875f
title: Deletion reviews require structural absence proof
categories:
- pitfall
- process
- tool-usage
confidence: 0.86
state: curated
scope_agents:
- verifier
- collector
- builder
source_agent: copilot
created_at: '2026-05-17T01:36:03.958942Z'
updated_at: '2026-05-17T01:48:10.855773Z'
approved_at: null
---

For dead-code or deletion tasks, passing tests are insufficient proof. Require structural absence checks such as `rg` over source/tests/docs, import graph checks, or API surface comparisons so removed code is not still reachable or duplicated elsewhere.
