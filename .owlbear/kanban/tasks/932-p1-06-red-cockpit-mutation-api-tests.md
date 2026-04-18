---
id: 932
title: 'P1-06: RED — Cockpit mutation API tests'
status: research
priority: important
created: 2026-04-17T19:58:25.607234+00:00
updated: 2026-04-17T19:58:25.607234+00:00
tags:
- cockpit
- backend
- phase-1
- type:test
parent: 920
depends_on:
- 930
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Write failing tests for cockpit mutation endpoints: move, edit (allowlisted YAML + body), release. Includes conflict detection (D9) and audit logging.

## Acceptance Criteria

- [ ] Test file at `tests/test_cockpit_mutation_api.py`
- [ ] Tests use FastAPI TestClient
- [ ] Tests cover:
  - `POST /api/tasks/{id}/move` with target status; validates against valid_transitions
  - `POST /api/tasks/{id}/move` with invalid target returns 422
  - `POST /api/tasks/{id}/edit` with allowlisted fields: title, tags, priority, depends_on, parent, block_reason, body
  - `POST /api/tasks/{id}/edit` with non-allowlisted field returns 422
  - `POST /api/tasks/{id}/edit` requires `updated` snapshot in request body
  - `POST /api/tasks/{id}/edit` returns 409 Conflict when `updated` snapshot is stale (D9)
  - `POST /api/tasks/{id}/release` unclaims task successfully
  - `POST /api/tasks/{id}/release` on unclaimed task returns appropriate error
  - Block mutation: edit with `block_reason` sets blocked state
  - Unblock mutation: edit with `block_reason: null` clears blocked state
  - All mutations write entry to `activity.jsonl` with `actor: "cockpit"`
  - 404 for mutations on non-existent task ID
- [ ] All tests fail (RED phase)

## Files

- `tests/test_cockpit_mutation_api.py`