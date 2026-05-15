---
id: 046989ef-cca5-4068-a265-7b474f36b556
title: create_task root parent omission
categories:
- tool-usage
- pitfall
confidence: 0.9
state: deleted
scope_agents:
- planner
- orchestrator
- builder
- reviewer
source_agent: planner
created_at: '2026-05-14T18:28:03.305473Z'
updated_at: '2026-05-15T20:56:34.770970Z'
approved_at: null
---

Kanban `create_task` can reject explicit `parent: null` as `ERR_PARENT_NOT_FOUND` for parent `0`. For root tasks, omit the parent field entirely; use explicit positive parent IDs only for child tasks.
