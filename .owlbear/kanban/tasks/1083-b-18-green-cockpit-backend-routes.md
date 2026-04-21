---
id: 1083
title: 'B-18: GREEN — cockpit backend routes'
status: todo
priority: important
created: 2026-04-21T10:50:53.767229+00:00
updated: 2026-04-21T10:50:53.767229+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- scope:cockpit
- tdd:green
parent: 1044
depends_on:
- 1082
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §5
Module: `serve/cockpit/src/owlbear_cockpit/routes/kanban.py`

Implement FastAPI cockpit backend routes wrapping CockpitView. Error mapping: KanbanError subclass → HTTP status (NotFoundError → 404, ValidationError → 422, ConcurrencyError → 409, ConfigError → 500). Request schemas enforce AC-NEW-24 (no `status` field on edit body).

Routes rewire existing cockpit backend from legacy engine to CockpitView facade. Existing routes (/api/board, /api/tasks, /api/tasks/{id}, /api/sessions) are updated; new routes added for admin operations.

## Acceptance Criteria

- [ ] All RED tests from B-17 (#1082) pass
- [ ] AC-NEW-24: Edit request Pydantic schema excludes `status` field → 422 on inclusion
- [ ] Error mapping: NotFoundError → 404, ValidationError → 422, ConcurrencyError → 409
- [ ] OCC: `expected_updated` passed from request body to CockpitView
- [ ] Read routes: GET /api/tasks, GET /api/tasks/{id} return envelope responses
- [ ] Activity routes: GET /api/activity (filtered), GET /api/sessions (SessionRecord)
- [ ] Admin routes: POST .../release, POST .../sweep, POST .../scan, POST .../repair, POST .../compact-activity
- [ ] DI pattern maintained: `get_engine` override in tests per existing cockpit convention