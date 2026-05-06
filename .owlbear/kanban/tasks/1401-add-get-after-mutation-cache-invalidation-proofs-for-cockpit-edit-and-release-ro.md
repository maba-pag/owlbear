---
id: 1401
title: Add GET-after-mutation cache invalidation proofs for cockpit edit and 
  release routes
status: backlog
priority: nice-to-have
created: 2026-05-06T03:40:00.756804+00:00
updated: 2026-05-06T04:10:44.705038+00:00
tags:
- cockpit
- cache
- test
parent:
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-06T04:10:44.705038+00:00
archival_reason:
archival_refs: []
---

## Context

Follow-up from #1346 reviewer recommendation #2. Currently only the move-route has a GET `/api/tasks` assertion proving cache invalidation after `POST /api/tasks/{id}/move` (at `tests/test_cockpit_cache_sse_1346.py:565`). Edit and release routes lack matching proofs.

## Acceptance Criteria

1. A test proves that `GET /api/tasks` reflects title changes after a successful `POST /api/tasks/{id}/edit` with a title mutation. The cached task list must show the updated title, not the pre-edit value.
2. A test proves that `GET /api/tasks` reflects tag changes after a successful `POST /api/tasks/{id}/edit` with a tags mutation. The cached task list must show the updated tags.
3. A test proves that `GET /api/tasks` reflects claimed-state changes after a successful `POST /api/tasks/{id}/release`. The cached task list must show the task as unclaimed after release.
4. All new tests follow the existing pattern at `test_cockpit_cache_sse_1346.py:565`: prime cache via initial GET, perform mutation via POST route, then assert refreshed GET reflects the change.
5. Existing tests remain green; no weakening of existing assertions.

## Key Files

- `tests/test_cockpit_cache_sse_1346.py` — existing move-route proof pattern to follow
- `tests/test_cockpit_mutation_api.py` — existing edit/release route tests (POST-only, no GET proof)
- `serve/cockpit/src/owlbear_cockpit/routes/read.py` — cache invalidation logic under proof

## Scope

- **In scope:** Test-only additions proving GET-after-mutation cache invalidation for edit (title, tags) and release (claimed state).
- **Out of scope:** Implementation changes to cache.py, read.py, or mutation routes. Cache populate ordering hardening (separate concern tracked in #1346 follow-up recommendation #1).