---
id: 1445
title: 'P4-08: Make pick_tasks read-only and keep start_work as claim writer'
status: backlog
priority: critical
created: 2026-05-08T19:32:02.327561+00:00
updated: 2026-05-08T19:36:13.639977+00:00
tags:
- phase-4
- scope:kanban
- type:refactor
- dispatch
- claims
- deployment-readiness
parent: 1437
depends_on:
- 1444
- 1439
- 1443
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: AgentView.pick_tasks, legacy dispatch helper behavior as needed, and start_work claim reclamation boundaries.
Out of scope: explicit resolve_drs MCP tool, Cockpit maintenance cleanup, and docs.

## Acceptance Criteria
1. AgentView.pick_tasks returns dispatch waves without calling sweep, repair_storage, resolve_pending_drs, edit_task, move_task, write_task, or task archival helpers.
2. Given an unblocked backlog task with expired claimed_at and no unresolved dependencies, AgentView.pick_tasks returns the task in a wave and leaves claimed_at unchanged on disk.
3. Given a pending DR whose response is approved, AgentView.pick_tasks leaves the DR file in decisions/pending and leaves the linked task body and blocked fields unchanged.
4. AgentView.start_work remains the writer that clears an expired claim and applies the caller's claim in one compare-and-swap retry loop.
5. Builder verifies AC-1 through AC-4 using the probe artifacts from #1444 and does not use pytest or vitest as the functional proof.