---
id: 1386
title: 'P2-11: Test Cockpit decision data contract and refetch flow'
status: backlog
priority: needed
created: 2026-05-06T01:04:46.991799+00:00
updated: 2026-05-06T01:06:57.303109+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:test
- frontend
- decisions
- interface-contract
parent: 1363
depends_on:
- 1367
- 1375
- 1385
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write frontend tests for the pending decision data contract and post-resolution refetch behavior.

## Problem Evidence
- usePendingDRs omits body even though the backend returns it and ResolveModal needs it.
- ResolveModal only refetches pending decision requests after resolution, not affected task or board state.
- Decision frontend errors must use the frontend error contract from #1375.

## Acceptance Criteria
- Tests prove pending decision types include the full body returned by the backend.
- Tests prove pending decision data preserves task link/context, agent or request type, age, body or preview content, and status needed by the UI.
- Tests prove successful resolution refetches pending decisions and affected task or board state after backend lifecycle side effects from #1385.
- Tests prove loading, empty, and expected error states consume the frontend error contract from #1375.
- The proof fails against the audited missing-body and decisions-only refetch behavior and is suitable for #1387 to satisfy.

## Scope
- In scope: Cockpit frontend decision hooks, types, API adapters, and refetch-flow tests.
- Out of scope: backend decision lifecycle from #1385, visible viewport redesign from #1389, task detail workflows, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1387.
