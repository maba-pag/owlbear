---
id: 1443
title: 'P4-06: Replace next_id config allocation and hard-code activity logging'
status: backlog
priority: needed
created: 2026-05-08T19:31:58.431269+00:00
updated: 2026-05-08T19:35:39.773310+00:00
tags:
- phase-4
- scope:kanban
- type:refactor
- id-allocation
- activity
- deployment-readiness
parent: 1437
depends_on:
- 1442
- 1439
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: kanban storage ID allocation, create_task persistence, and activity logging defaults.
Out of scope: MCP schema, Cockpit UI, setup seed, and docs.

## Acceptance Criteria
1. storage.allocate_next_id or its replacement computes the next ID by scanning active and archive task filename prefixes under the create lock, then returns max prefix plus one.
2. KanbanEngine.create_task no longer reads or writes config.next_id, and a scratch board can create tasks when config.yml is absent.
3. Given active task prefixes 1 and 3 plus archive prefixes 2 and 5, KanbanEngine.create_task writes a task with ID 6.
4. Concurrent create_task calls under one scratch board produce distinct task filename prefixes and leave config.yml absent or unchanged.
5. KanbanEngine activity logging is enabled without config authority, and create_task appends a mutation event containing task_id, action, source, detail, and timestamp.
6. Builder verifies AC-1 through AC-5 using the probe artifacts from #1442 and does not use pytest or vitest as the functional proof.