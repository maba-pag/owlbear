---
id: 1660
title: 'P1-01: Backend Ideas API — GET/PUT /api/ideas with DI and atomic_write'
status: backlog
priority: needed
created: 2026-05-18T17:41:31.832363+02:00
updated: 2026-05-18T17:42:26.397797+02:00
tags:
  - phase-1
  - scope:cockpit
  - backend
parent: 1658
depends_on:
  - 1638
ac:
  - 'GET `/api/ideas` returns `{"content": "..."}` with file contents when `.owlbear/ideas.md`
    exists; returns `{"content": ""}` when file is absent'
  - 'PUT `/api/ideas` accepts `{"content": "..."}` body, writes via `atomic_write`
    imported from `owlbear_kanban.storage_io`, creates file on first write when absent,
    and returns HTTP 204'
  - '`get_ideas_path` dependency returns a `Path` and is overridable via `app.dependency_overrides`
    for test isolation'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

Brief: see parent #1658 (`.owlbear/briefs/draft-cockpit-ideas/brief.md`)

Route module at `serve/cockpit/src/owlbear_cockpit/routes/ideas.py` with bare `APIRouter()`. Prefix applied at mount in `main.py` per existing cockpit convention.

Request/response models: Pydantic `BaseModel` with `ConfigDict(extra="forbid")` per existing cockpit convention.

`get_ideas_path` resolves to `kanban_dir.parent / "ideas.md"` (`.owlbear/ideas.md`).

## In Scope

- Route module with GET and PUT endpoints
- `get_ideas_path` DI dependency
- Pydantic request/response models
- Router mount in `main.py`

## Out of Scope

- Frontend consumption (separate task)
- SSE/file-watcher (not needed per brief)
- OCC/versioning (last-write-wins accepted)