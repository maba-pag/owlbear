---
id: 1189
title: 'P3-01: Test decisions API endpoints'
status: research
priority: needed
created: 2026-04-30T00:52:09.506007+00:00
updated: 2026-04-30T00:55:04.832515+00:00
tags:
- phase-3
- scope:cockpit
- type:test
parent: 1179
depends_on: []
blocked: false
block_reason:
claimed_by: dim-stream
claimed_at: 2026-04-30T00:55:04.832515+00:00
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Test `GET /api/decisions/pending` returns JSON with `count` and `items` array
- Test response item shape: id, task_id, agent, request_type, created, title, body_preview
- Test body_preview is truncated to ~200 chars
- Test returns empty list when no pending DRs exist
- Test `POST /api/decisions/{id}/resolve` accepts response enum + optional notes
- Test resolve updates file: changes response field, appends ## Response section
- Test resolve returns 404 for non-existent DR id
- Test resolve validates response enum (rejects invalid values)

## Scope

- IN: Cockpit API endpoint tests (`serve/cockpit/`)
- OUT: frontend components, decisions.py unit tests

Brief: see parent #1179
