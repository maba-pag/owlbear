---
approved_at: '2026-05-16T03:57:45.671762Z'
categories: [process, pitfall, tool-usage]
confidence: 0.91
contested_by_task: null
created_at: '2026-05-14T13:37:16.130927Z'
didnt_use_count: 21
id: 867e783e-8fb6-478e-9f9e-9704d595c336
outstanding_count: 0
scope_agents: [verifier]
score: 0.91
source_agent: reviewer
state: approved
title: Parent coordination closures need full child-set verification
unremarkable_count: 0
updated_at: '2026-07-24T15:38:13.515447+00:00'
---

Do not PASS a parent coordination task from a builder note or `list_tasks(parent=ID)` alone. Verify the exact delegated child set directly; if the child set is not explicitly recoverable from task metadata, request deps or another explicit enumeration first. Confirm every child is completed or archived, and separately confirm the named consolidation gate task is completed or archived before routing the parent onward.
