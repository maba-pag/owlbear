---
id: 934
title: 'P1-07: GREEN — Cockpit mutation API'
status: research
priority: important
created: 2026-04-17T19:58:48.844016+00:00
updated: 2026-04-17T19:58:48.844016+00:00
tags:
- cockpit
- backend
- phase-1
- type:build
parent: 920
depends_on:
- 932
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Implement cockpit mutation endpoints to pass RED tests from #932.

## Acceptance Criteria

- [ ] `POST /api/tasks/{id}/move` calls engine `move_task` after validating target against `valid_transitions`
- [ ] `POST /api/tasks/{id}/edit` updates allowlisted YAML fields (title, tags, priority, depends_on, parent, block_reason) + body via engine `edit_task`
- [ ] Edit endpoint checks `updated` timestamp before write: re-reads task, compares `updated` to request snapshot; returns 409 Conflict if stale (D9)
- [ ] `POST /api/tasks/{id}/release` calls engine `release_task` unconditionally (D12)
- [ ] Block: edit with `block_reason` value calls engine block; edit with `block_reason: null` calls engine unblock
- [ ] All mutations log to `activity.jsonl` with `actor: "cockpit"` via engine's existing logging path
- [ ] Pydantic request models enforce field allowlist (no arbitrary field injection)
- [ ] 404 for non-existent task; 422 for invalid input
- [ ] All RED tests from #932 pass
- [ ] Boundary test (#924) still passes

## Files

- `serve/cockpit/src/owlbear_cockpit/routes/mutate.py`
- `serve/cockpit/src/owlbear_cockpit/models.py` (request models)
- `serve/cockpit/src/owlbear_cockpit/adapter.py` (mutation wrappers added)