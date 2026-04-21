---
id: 1082
title: 'B-17: RED — cockpit backend route tests'
status: todo
priority: needed
created: 2026-04-21T10:50:43.401807+00:00
updated: 2026-04-21T10:50:43.401807+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- scope:cockpit
- tdd:red
parent: 1044
depends_on:
- 1081
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §5, AC-NEW-24
Module: `tests/test_cockpit_kanban_routes.py`

Test FastAPI cockpit backend routes that wrap CockpitView methods. Routes include: task reads (GET /api/tasks, GET /api/tasks/{id}), OCC mutations (POST /api/tasks/{id}/edit, POST /api/tasks/{id}/move), admin operations (POST /api/tasks/{id}/release, POST /api/tasks/sweep), activity/session reads (GET /api/activity, GET /api/sessions), and maintenance (POST /api/tasks/scan, POST /api/tasks/repair, POST /api/tasks/compact-activity).

## Acceptance Criteria

- [ ] AC-NEW-24: `POST /api/tasks/{id}/edit` with `status` in request body → HTTP 422 (Pydantic rejects before engine)
- [ ] OCC mutations pass `expected_updated` from request body to CockpitView
- [ ] ERR_STALE from CockpitView → HTTP 409 Conflict
- [ ] ERR_NOT_FOUND → HTTP 404
- [ ] ValidationError → HTTP 422
- [ ] ConfigError → HTTP 500
- [ ] GET /api/tasks returns ListTasksResponse envelope
- [ ] GET /api/tasks/{id} returns ShowTaskResponse envelope
- [ ] GET /api/activity returns filtered activity events
- [ ] GET /api/sessions returns SessionRecord list
- [ ] POST /api/tasks/{id}/release returns SingleTaskResponse
- [ ] POST /api/tasks/sweep returns list of released task IDs
- [ ] All tests fail (RED phase)