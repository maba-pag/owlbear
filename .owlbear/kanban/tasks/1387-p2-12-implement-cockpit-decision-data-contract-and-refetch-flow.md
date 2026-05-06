---
id: 1387
title: 'P2-12: Implement Cockpit decision data contract and refetch flow'
status: backlog
priority: needed
created: 2026-05-06T01:04:49.160414+00:00
updated: 2026-05-06T01:06:57.313331+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- decisions
- interface-contract
parent: 1363
depends_on:
- 1386
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement the pending decision frontend data contract and refetch behavior needed by the decision viewport.

## Problem Evidence
- usePendingDRs omits body even though the backend returns it and ResolveModal needs it.
- ResolveModal only refetches pending decision requests after resolution, not affected task or board state.
- Decision frontend errors must use the frontend error contract from #1375.

## Acceptance Criteria
- Pending decision frontend types include the full body returned by the backend.
- Pending decision data preserves task link/context, agent or request type, age, body or preview content, and status needed by the UI.
- Successful resolution refetches pending decisions and affected task or board state after backend lifecycle side effects from #1385.
- Loading, empty, and expected error states consume the frontend error contract from #1375.
- The implementation satisfies #1386 without building the visible viewport redesign owned by #1389.

## Scope
- In scope: Cockpit frontend decision hooks, types, API adapters, and refetch flow.
- Out of scope: backend decision lifecycle from #1385, visible viewport redesign from #1389, task detail workflows, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1386.
