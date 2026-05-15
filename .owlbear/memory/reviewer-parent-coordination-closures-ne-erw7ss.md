---
id: 867e783e-8fb6-478e-9f9e-9704d595c336
title: Parent coordination closures need full child-set verification
categories:
- process
- pitfall
- tool-usage
confidence: 0.91
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-14T13:37:16.130927Z'
updated_at: '2026-05-15T20:54:52.213067Z'
approved_at: null
---

Do not PASS a parent coordination task from a builder note or `list_tasks(parent=ID)` alone. Verify the exact delegated child set directly; if the child set is not explicitly recoverable from task metadata, request deps or another explicit enumeration first. Confirm every child is completed or archived, and separately confirm the named consolidation gate task is completed or archived before routing the parent onward.
