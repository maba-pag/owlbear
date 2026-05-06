---
id: 1384
title: 'P2-09: Test Cockpit decision lifecycle backend side effects'
status: backlog
priority: critical
created: 2026-05-06T01:04:42.356752+00:00
updated: 2026-05-06T01:06:57.292153+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-api
- type:test
- backend
- decisions
- lifecycle
parent: 1363
depends_on:
- 1371
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write backend tests for Cockpit decision resolution lifecycle side effects and error handling.

## Problem Evidence
- Cockpit routes manually parse and rewrite decision files while canonical lifecycle logic lives in owlbear_kanban.decisions.
- Cockpit resolve writes a response but does not immediately append the summary to the task, move the decision request to resolved, or unblock approved/rejected tasks.
- The GUI can therefore make resolution appear incomplete until later background lifecycle processing.

## Acceptance Criteria
- Tests cover pending approved resolution appending the summary, moving the decision request to resolved, unblocking the task, and returning predictable response data.
- Tests cover pending rejected resolution appending the summary, moving the decision request to resolved, unblocking the task, and returning predictable response data.
- Tests cover needs-info resolution appending the summary and moving the decision request to resolved while leaving the task blocked.
- Tests cover already-resolved, unknown, malformed, and duplicate-response cases with the backend error envelope from #1371 and correct status codes.
- Tests prove task side effects and decision-request file transitions are observable immediately after the Cockpit request completes.
- The proof fails against the audited incomplete lifecycle behavior and is suitable for #1385 to satisfy.

## Scope
- In scope: Cockpit backend decision resolution API tests and task side-effect assertions.
- Out of scope: frontend decision viewport, task-detail conflict workflows, scanner/cache/SSE invalidation, and unrelated decision-system redesign.

## Counterpart
Implementation task: #1385.
