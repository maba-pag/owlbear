---
id: 1370
title: 'P1-07: Test Cockpit backend error envelope and guidance contract'
status: backlog
priority: critical
created: 2026-05-06T00:58:41.555448+00:00
updated: 2026-05-06T01:00:31.474435+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-api
- type:test
- backend
- interface-contract
- guidance
parent: 1363
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Write backend tests that define the Cockpit error envelope and kanban guidance policy before implementation.

## Problem Evidence
- Cockpit mutation routes mostly return plain HTTPException detail strings, while kanban errors expose code and user_message.
- CockpitView clears guidance implicitly; the list route passes guidance on cache miss but drops it on cache hit.
- Frontend code currently branches on status codes and generic strings inconsistently.

## Acceptance Criteria
- Tests define a Cockpit-specific error response envelope with stable code and user-facing message fields.
- Tests cover representative expected errors for not found, stale/conflict, validation, invalid config, scanner failure, repair failure, and decision/admin failure behavior where applicable.
- Tests prove correct HTTP status codes are preserved while expected errors use the envelope.
- Tests define the policy for kanban/MCP guidance: which guidance is suppressed, transformed, or exposed to Cockpit users.
- The proof fails against the audited inconsistent behavior and is suitable for #1371 to satisfy.

## Scope
- In scope: Cockpit backend API contract tests for expected errors and guidance handling.
- Out of scope: frontend UI adoption, dashboard redesign, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1371.
