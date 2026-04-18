# Cockpit Read API — GREEN Phase

> **Owning task:** #930 — P1-05: GREEN — Cockpit read API + mtime-scan cache
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Implement cockpit read endpoints and mtime-scan cache to pass 30 RED tests
from #928. Key questions: (a) What architecture for routes, adapter, cache?
(b) How to handle the DI contract tests expect? (c) Mtime-scan cache design?
(d) Pydantic response models?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `tests/test_cockpit_read_api.py` — 30 RED tests defining the contract | 1.0 |
| S2 | `tests/test_cockpit_boundary.py` — import boundary constraints | 1.0 |
| S3 | `serve/kanban/src/owlbear_kanban/engine.py` — engine API + mtime cache pattern | 1.0 |
| S4 | `serve/kanban/src/owlbear_kanban/models.py` — Task, TaskSummary, BoardConfig | 1.0 |
| S5 | `.owlbear/research/928-cockpit-read-api-tests.md` — RED phase research | 0.9 |
| S6 | FastAPI dependency injection docs (standard pattern) | 0.8 |

## 3. Analysis

### 3.1 Test Contract Summary

Tests use `dependency_overrides[get_engine]` — the app must expose a `get_engine` DI
callable from `main.py`. 30 tests across 5 classes:

| Class | Tests | Endpoint | Key assertions |
|-------|-------|----------|----------------|
| `TestFromAC_BoardConfig` | 9 | `GET /api/board` | statuses list (ordered), priorities, valid_transitions dict |
| `TestFromAC_TaskList` | 13 | `GET /api/tasks` | tasks list + mtime int; status/priority/tag/blocked filters |
| `TestFromAC_TaskDetail` | 4 | `GET /api/tasks/{id}` | full Task fields, 404 with ID in detail |
| `TestFromAC_Sessions` | 5 | `GET /api/sessions` | sessions list, active/all filter, default=active |
| `TestFromAC_MtimeCache` | 3 | `GET /api/tasks` | mtime stable, changes on file edit |

### 3.2 Architecture Decision: File Layout

| Option | Layout | Pros | Cons |
|--------|--------|------|------|
| A: Single routes file | `routes/read.py` | Simple, matches AC file list | 4 endpoints in one file |
| B: Split by resource | `routes/board.py`, `routes/tasks.py`, `routes/sessions.py` | Clean separation | More files for simple wrappers |

**(rec:) Option A** — 4 read-only endpoints totaling ~60 LOC. Single file avoids
over-engineering. AC explicitly names `routes/read.py`. Confidence: .90

### 3.3 Adapter Design

The adapter wraps 5 engine methods. Two options:

| Option | Pattern | Pros | Cons |
|--------|---------|------|------|
| A: Thin functions | Module-level functions taking engine as arg | KISS, no class overhead | Functions scattered |
| B: Class wrapper | `CockpitAdapter(engine)` with methods | Groups methods, testable | Extra abstraction |

**(rec:) Option A** — YAGNI. Routes call engine directly via DI. The adapter module
provides `get_engine` + engine init logic. No extra class needed for 5 delegations
that are 1-2 lines each. Confidence: .85

### 3.4 Mtime-Scan Cache

The engine already has per-file mtime caching internally. The cockpit needs to:
1. Expose a directory-level mtime in the response (`max(st_mtime_ns)` across task files)
2. Optionally cache the full task list at the HTTP level

Two approaches:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Compute mtime in route | `os.scandir()` in the route, max mtime_ns, delegate to engine | Simple, engine handles its own cache | Scan + engine call on every request |
| B: Separate cache module | `cache.py` with `MtimeScanCache` — stores `{filename: mtime_ns}` dict, skips engine call if unchanged | Fewer engine calls, good for frequent polling | Extra module, but AC lists `cache.py` |

**(rec:) Option B** — AC explicitly lists `cache.py`. The cache does an `os.scandir()`
to build `{filename: mtime_ns}`, compares with previous snapshot, and only calls
`engine.list_tasks()` on change. Returns `(tasks, max_mtime_ns)`. This matches the
engine's own pattern and the AC wording. Confidence: .85

### 3.5 Pydantic Response Models

Tests assert specific shapes. Required models in `models.py`:

```
BoardResponse:  statuses: list[StatusInfo], priorities: list[str],
                defaults: dict, valid_transitions: dict[str, list[str]]
TaskListResponse: tasks: list[TaskSummaryOut], mtime: int
TaskDetailResponse: (all Task fields — reuse or re-export)
SessionListResponse: sessions: list[SessionOut]
StatusInfo: name: str
TaskSummaryOut: id, title, status, priority, tags, blocked, ...
SessionOut: task_id: int, state: str, agent: str, ...
```

### 3.6 Boundary Compliance

Forbidden imports: `claim_task`, `start_work`, `end_work`, `pick_dispatchable` from
`owlbear_kanban*`. All read methods (`list_tasks`, `show_task`, `board_config`,
`valid_transitions`, `list_sessions`, `KanbanEngine`, models) are allowed.

### 3.7 DI Contract

Tests import `get_engine` from `owlbear_cockpit.main`. This function must:
- Be a callable that returns a `KanbanEngine` instance
- Be usable as a FastAPI `Depends()` parameter
- Be importable directly (for `dependency_overrides`)

Standard pattern: `def get_engine() -> KanbanEngine: return app.state.engine`

## 4. Recommendation

Proceed with: single `routes/read.py`, thin adapter functions (no class), separate
`cache.py` with `MtimeScanCache`, Pydantic response models in `models.py`, and
`get_engine` DI callable in `main.py`. Confidence: .87

Challenge: SKIPPED — implementation follows established patterns from RED research
(#928), no significant new architectural choice.

## 5. Follow-up Tasks

- #930 advances to backlog for architect review, then GREEN implementation
- No additional tasks — AC is self-contained, all files are scoped
