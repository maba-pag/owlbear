---
approved_at: null
categories: [pitfall, process]
confidence: 0.85
contested_by_task: null
created_at: '2026-05-27T22:47:19.568286Z'
didnt_use_count: 1
id: 2110335a-8024-41cc-b379-faaffb4784ad
outstanding_count: 0
scope_agents: [shaper, verifier]
score: 0.89
source_agent: reviewer
state: deleted
title: Unrelated pytest collection failures are proof-plan defects
unremarkable_count: 0
updated_at: '2026-07-14T23:57:25.707304+00:00'
---

When a shaped pytest command collects unrelated failures before reaching the owned slice, treat the selector as a shaper-owned proof-plan defect. Use the narrowest path-scoped command that exercises the claimed boundary.
