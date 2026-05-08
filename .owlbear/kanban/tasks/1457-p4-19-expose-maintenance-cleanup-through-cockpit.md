---
id: 1457
title: 'P4-19: Expose maintenance cleanup through Cockpit'
status: backlog
priority: needed
created: 2026-05-08T19:37:26.531942+00:00
updated: 2026-05-08T19:38:42.640532+00:00
tags:
- phase-4
- scope:cockpit
- type:build
- cleanup
- maintenance
- deployment-readiness
parent: 1437
depends_on:
- 1448
- 1449
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: Cockpit maintenance API and UI surface for user-triggered cleanup.
Out of scope: kanban cleanup internals, MCP schema changes, docs, and agent guidance.

## Acceptance Criteria
1. POST /api/tasks/cleanup invokes the kanban cleanup operation from #1449 only when the endpoint is called, and returns released_claim_ids, archived_task_ids, and skipped_items fields.
2. Cockpit view and route layers expose the cleanup response without converting skipped_items into a generic error.
3. The Cockpit maintenance UI presents a user-triggered cleanup control and displays counts for released claims, archived tasks moved, and skipped items after completion.
4. Cockpit startup, board read endpoints, task list refresh, and SSE event streaming do not trigger cleanup.
5. Builder verifies AC-1 through AC-4 using the probe artifacts from #1448 and does not use pytest or vitest as the functional proof.