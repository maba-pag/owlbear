---
id: 1385
title: 'P2-10: Implement Cockpit decision lifecycle backend unification'
status: backlog
priority: critical
created: 2026-05-06T01:04:45.316826+00:00
updated: 2026-05-06T01:06:57.297838+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-api
- type:fix
- backend
- decisions
- lifecycle
parent: 1363
depends_on:
- 1384
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Unify Cockpit decision resolution with the canonical kanban decision lifecycle.

## Problem Evidence
- Cockpit routes manually parse and rewrite decision files while canonical lifecycle logic lives in owlbear_kanban.decisions.
- Cockpit resolve writes a response but does not immediately append the summary to the task, move the decision request to resolved, or unblock approved/rejected tasks.
- The GUI can therefore make resolution appear incomplete until later background lifecycle processing.

## Acceptance Criteria
- Cockpit decision resolution reuses or promotes shared canonical decision lifecycle helpers instead of duplicating parser/writer behavior where feasible.
- Approved and rejected resolutions immediately append the summary, move the decision request to resolved, unblock the task, and return predictable response data.
- Needs-info resolution appends the summary and moves the decision request to resolved while leaving the task blocked, matching canonical semantics.
- Already-resolved, unknown, malformed, and duplicate-response cases return the backend error envelope from #1371 with correct status codes.
- The implementation satisfies #1384 without changing unrelated decision lifecycle semantics.

## Scope
- In scope: Cockpit backend decision resolution route behavior and shared lifecycle integration.
- Out of scope: frontend decision viewport, task-detail conflict workflows, scanner/cache/SSE invalidation, and unrelated decision-system redesign.

## Counterpart
Test task: #1384.
