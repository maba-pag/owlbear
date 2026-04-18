# Cockpit Read API Tests — RED Phase

> **Owning task:** #928 — P1-04: RED — Cockpit read API tests
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #928 requires RED-phase failing tests for cockpit read-only HTTP endpoints:
board config, task list (with filters and mtime), task detail, and sessions.

Key questions: (a) What test architecture and fixtures? (b) What response schemas
should tests assert? (c) How do tests fail in RED phase? (d) How to test mtime
cache validation?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `tests/test_cockpit_boundary.py` — existing cockpit TestClient pattern | 1.0 |
| S2 | `serve/kanban/src/owlbear_kanban/engine.py` — engine read API surface | 1.0 |
| S3 | `serve/kanban/src/owlbear_kanban/models.py` — Task, TaskSummary, BoardConfig | 1.0 |
| S4 | `serve/kanban/tests/test_list_sessions.py` — board fixture pattern | 0.9 |
| S5 | `serve/kanban/tests/test_idtofilename_cache_943.py` — engine fixture + mtime | 0.8 |
| S6 | FastAPI docs: TestClient, dependency_overrides | 0.9 |

## 3. Analysis

### 3.1 Current Cockpit State

- `main.py`: only `/health` endpoint. No routes for `/api/*`.
- `adapter.py`: empty placeholder.
- Boundary test (AC#5) forbids importing `claim_task`, `start_work`, `end_work`,
  `pick_dispatchable` from `owlbear_kanban*`. Read operations are allowed.

### 3.2 Test Architecture

| Option | Pattern | Pros | Cons |
|--------|---------|------|------|
| A: `dependency_overrides` | FastAPI standard DI — define `get_engine()` dep, override in tests | Idiomatic, decoupled, testable | Requires DI point in app (defined in GREEN) |
| B: `app.state` | Set engine on `app.state.engine`, access in routes | Simple, no DI framework | Couples tests to internal state |
| C: Monkeypatch adapter | `monkeypatch.setattr("owlbear_cockpit.adapter.engine", ...)` | No app changes needed | Fragile, ties to implementation |

**(rec:) Option A** — standard FastAPI pattern, clean separation. Tests define
what the DI contract looks like; GREEN implements it. Confidence: .90

### 3.3 RED Failure Mode

Tests will fail because:
1. Routes don't exist → `GET /api/tasks` returns 404 (not the asserted 200)
2. DI dependency doesn't exist → fixture setup may fail with `ImportError`

Both are valid RED failures. Recommendation: structure tests so the HTTP-level
404 is the primary failure (more informative for the GREEN implementor).

### 3.4 Response Schemas (derived from AC + engine models)

| Endpoint | Response Schema | Source |
|----------|----------------|--------|
| `GET /api/board` | `{"statuses": [{"name": str}], "priorities": [str], "defaults": {"status": str, "priority": str}, "valid_transitions": {status: [str]}}` | BoardConfig + valid_transitions |
| `GET /api/tasks` | `{"tasks": [TaskSummary], "mtime": int}` | AC: "TaskSummary list + tasks-dir mtime" |
| `GET /api/tasks?status=...` | Same shape, filtered | AC: status/priority/tag/blocked filters |
| `GET /api/tasks/{id}` | Full Task dict with `updated` field | AC: "full task with updated timestamp" |
| `GET /api/tasks/{id}` (404) | `{"detail": str}` with HTTP 404 | AC: "non-existent ID returns 404" |
| `GET /api/sessions?filter=active` | `{"sessions": [{"task_id": int, "state": str}]}` | WorkSession model |
| `GET /api/sessions?filter=all` | Same shape, unfiltered | AC |

### 3.5 Fixture Design

Reuse the board-setup pattern from kanban tests (S4, S5):

```
@pytest.fixture → tmp_path board with config.yml + 3 task files
@pytest.fixture → KanbanEngine(board, agent_name="test")
@pytest.fixture → TestClient(app) with engine overridden
```

Task files should cover: different statuses, tags, priorities, blocked state —
enabling filter tests without creating new data per test.

### 3.6 Mtime Cache Test

The engine tracks `st_mtime_ns` per file internally. The endpoint should expose
a directory-level mtime (max of file mtimes or dir stat). Test approach:

1. GET `/api/tasks` → note `mtime` in response
2. GET `/api/tasks` again (no changes) → assert same `mtime`
3. Touch a task file → GET again → assert `mtime` changed

## 4. Recommendation

**Proceed with Option A** (dependency_overrides pattern). Confidence: .90

The test file should define 3 fixtures (board, engine, client) and ~10 test
methods covering all 8 AC items. Tests will naturally fail RED because routes
don't exist. No architecture decisions needed — this follows established patterns.

Challenge: SKIPPED — info-only research for established test patterns, no
significant architectural choice.

## 5. Follow-up Tasks

- **#928 itself** → advances to backlog for architect review, then RED implementation
- No additional follow-up tasks needed — the AC is self-contained
