---
id: 1447
title: 'P4-10: Add retry-safe resolve_drs MCP operation'
status: backlog
priority: critical
created: 2026-05-08T19:32:07.308897+00:00
updated: 2026-05-08T19:36:55.071556+00:00
tags:
- phase-4
- scope:mcp-kanban
- type:build
- decisions
- deployment-readiness
parent: 1437
depends_on:
- 1446
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
In scope: owlbear_kanban.decisions resolver behavior and owlbear_mcp_kanban resolve_drs tool exposure.
Out of scope: Cockpit decision route changes, agent guidance text, and list/filter normalization.

## Acceptance Criteria
1. owlbear_mcp_kanban.server registers resolve_drs as an explicit MCP tool that resolves pending DR files with non-pending responses and returns a structured result containing moved relative paths and a resolved count.
2. resolve_drs handles approved and rejected responses by appending one canonical summary, unblocking the linked task, and moving the DR file to decisions/resolved.
3. resolve_drs handles needs-info by appending one canonical summary, keeping the linked task blocked, and moving the DR file to decisions/resolved.
4. A repeated resolve_drs call for a DR already in decisions/resolved does not append a duplicate canonical summary to the linked task.
5. AgentView.pick_tasks and MCP pick_tasks contain no call path to resolve_pending_drs or resolve_drs.
6. Builder verifies AC-1 through AC-5 using the probe artifacts from #1446 and does not use pytest or vitest as the functional proof.