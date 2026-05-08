---
id: 1451
title: 'P4-14: Normalize MCP filters, annotations, and errors'
status: backlog
priority: needed
created: 2026-05-08T19:32:19.525089+00:00
updated: 2026-05-08T19:39:25.163315+00:00
tags:
- phase-4
- scope:mcp-kanban
- type:build
- filters
- errors
- annotations
- validation
- deployment-readiness
parent: 1437
depends_on:
- 1450
- 1445
- 1447
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: AgentView/MCP interface behavior for list filters, status-destination validation, annotations, descriptions, and error envelopes.
Out of scope: Cockpit UI, setup seed, agent guidance, and docs.

## Acceptance Criteria
1. list_tasks treats ids=[] as an explicit empty ID request and returns an empty tasks list without falling back to unfiltered board listing.
2. list_tasks with archival_reason and no status argument searches archive storage and returns tasks whose archival_reason matches the requested product archive reason.
3. move_task and end_work destination handling use one shared validation path for status names, archive reason requirements, archive refs, completed-only archival, and predicate failures.
4. MCP tool annotations and descriptions state that move_task is mutating and not idempotent, pick_tasks is read-only after dispatch side effects are removed, and resolve_drs performs DR mutation.
5. MCP errors for KanbanError, Pydantic validation, malformed ID, and stale write cases surface structured code and message fields without raw tracebacks or internal paths.
6. Builder verifies AC-1 through AC-5 using the probe artifacts from #1450 and does not use pytest or vitest as the functional proof.