---
id: 1939
title: 'P1-02: Kanban request storage health'
status: build
priority: medium
created: 2026-07-17T02:31:44.655319+02:00
updated: 2026-07-17T02:33:38.504303+02:00
tags:
  - phase-1
  - scope:kanban
  - requests
parent: 1945
depends_on:
  - 1937
ac:
  - Given malformed pending/resolved request files and duplicate request IDs, 
    the request-health public method returns path-specific schema/read findings 
    and the complete duplicate path set without changing storage.
  - Given requests whose owners are active, archived, or absent, the method 
    treats active/archive owners as present and reports only the absent owner 
    with request ID and task ID.
  - Given completed content in pending storage and unresolved content in 
    resolved storage, the method reports the location mismatch for each record.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Make malformed, duplicated, orphaned, and location-drifted decision/action request records observable through a read-only Kanban diagnostic boundary instead of log-only skipping.

## Scope
In scope: Kanban request parsing, identity evidence, task-owner resolution, and pending/resolved location diagnostics. Out of scope: request mutation, task-file repair, Cockpit HTTP aggregation, and UI behavior.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the workspace-health spec and accepted design. Task identity evidence is supplied by parent dependency #1937.

## Proof Guidance
Use a focused real-filesystem Kanban request behavior check through the public request-health boundary. Add durable coverage only where malformed-record observability or complete duplicate-set handling is otherwise unprotected.