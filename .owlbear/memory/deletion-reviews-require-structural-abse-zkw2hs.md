---
approved_at: null
categories: [pitfall, process, tool-usage]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-17T01:36:03.958942Z'
didnt_use_count: 2
id: 5d25d9b0-6f22-4108-be32-7ae6f6c3875f
outstanding_count: 0
scope_agents: [verifier, collector, builder]
score: 0.86
source_agent: copilot
state: deleted
title: Deletion reviews require structural absence proof
unremarkable_count: 0
updated_at: '2026-07-14T20:10:04.486554+00:00'
---

For dead-code or deletion tasks, passing tests are insufficient proof. Require structural absence checks such as `rg` over source/tests/docs, import graph checks, or API surface comparisons so removed code is not still reachable or duplicated elsewhere.
