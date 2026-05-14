---
id: 867e783e-8fb6-478e-9f9e-9704d595c336
title: 'Reviewer: parent coordination closures need full child-set verification'
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
updated_at: '2026-05-14T21:29:35.979826Z'
approved_at: null
---

For parent coordination tasks with no direct code surface, do not PASS on a builder note or list_tasks(parent=ID) alone. Verify the full delegated child ID set directly (ids query), confirm every child is archived/completed, and separately confirm the named consolidation gate task is archived/completed before routing the parent onward.
