---
id: 1449
title: 'P4-12: Add user-triggered cleanup for expired claims and archived moves'
status: backlog
priority: needed
created: 2026-05-08T19:32:12.180001+00:00
updated: 2026-05-08T19:38:27.357984+00:00
tags:
- phase-4
- scope:kanban
- type:build
- cleanup
- archive
- claims
- deployment-readiness
parent: 1437
depends_on:
- 1448
- 1445
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: kanban engine cleanup primitive for expired claims and active archived-file movement.
Out of scope: Cockpit route/UI wiring, MCP schema changes, docs, and agent guidance.

## Acceptance Criteria
1. KanbanEngine exposes a user-triggered maintenance cleanup operation that releases expired claimed_at values through compare-and-swap and returns released_claim_ids.
2. The cleanup operation moves active task files whose status is archived into archive storage when archival metadata satisfies the product archive-reason contract, and returns archived_task_ids.
3. The cleanup operation skips malformed task files and archive destination collisions, leaves the source task file in place, and returns one skipped_items entry per skipped file with path and reason fields.
4. pick_tasks, start_work, KanbanEngine initialization, and MCP server startup do not invoke the cleanup operation implicitly.
5. Builder verifies AC-1 through AC-4 using the probe artifacts from #1448 and does not use pytest or vitest as the functional proof.