# Research: Tests for dep-status guidance in start_work

> **Owning task:** #1526 — P1-01: tests for dep-status guidance in start_work (AC1-AC3)
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1526 requires unit tests (TDD RED) for a planned `start_work()` dep-status guidance feature. The implementation will iterate `task.depends_on`, compute dep-status via existing `_compute_dep_status()`, and emit a guidance string when blocked.

**Research question:** What's the recommended test structure, mocking strategy, and file placement for AC1-AC3?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/kanban/tests/test_engine_coverage.py` L2210-2245 | Existing `start_work` tests | 1.0 |
| 2 | `serve/kanban/tests/test_engine_coverage.py` L2182-2288 | Guidance assertion patterns | 1.0 |
| 3 | `serve/kanban/tests/test_engine_pick_tasks.py` L240-530 | `depends_on` fixture patterns | 0.9 |
| 4 | `serve/kanban/src/owlbear_kanban/agent_view.py` L214-228 | Dep iteration + exception tuple | 1.0 |
| 5 | `serve/kanban/src/owlbear_kanban/engine.py` L663-699 | `_compute_dep_status()` logic | 0.9 |
| 6 | `serve/kanban/tests/test_engine_move_claim.py` L615-871 | Mock/patch patterns | 0.8 |

## 3. Analysis

### Test Setup Pattern

All kanban tests use local helpers (`_make_board`, `_write_task`) — no shared conftest fixtures. Each test file is self-contained. The existing `test_engine_coverage.py` pattern:

```python
board = _make_board(tmp_path)
_write_task(board, task_id=1, depends_on="[99]")
_write_task(board, task_id=99, status="todo")  # active dep
engine = KanbanEngine(board, activity_log=False)
resp = engine.agent_view().start_work(1)
```

### AC1: Dep-blocked → guidance string

| Approach | Feasibility | Notes |
|----------|-------------|-------|
| Real dep on filesystem (active task) | High | `_write_task(board, task_id=99, status="todo")` — natural "blocked" |
| `_compute_dep_status` returns "blocked" | Confirmed | Active dep_id in `active_ids` → immediate "blocked" |

Test assertion: `assert len(resp.guidance) == 1` + regex match on format string with int IDs.

### AC2: No deps / resolved deps → guidance == []

| Scenario | Setup |
|----------|-------|
| No deps | `_write_task(board, task_id=1, depends_on="[]")` |
| All resolved | dep archived with `archival_reason="completed"` (maps to "ok") |

Both scenarios currently pass trivially (guidance is always []) — valid TDD: they lock the regression path.

### AC3: Exception resilience — 4 exception types

| Exception | Natural trigger | Mock needed? |
|-----------|----------------|-------------|
| `FileNotFoundError` | Dep ID references non-existent task | No |
| `CorruptionError` | Write malformed YAML for dep | Possible, but complex |
| `ValueError` | Rare edge case in show_task | Yes — patch |
| `KeyError` | Rare edge case in show_task | Yes — patch |

**Recommended strategy:** Use `unittest.mock.patch.object(engine, "show_task")` with `side_effect` that raises the target exception for specific dep IDs. Cleaner than writing corrupt files for each type.

### File Placement

New file: `serve/kanban/tests/test_start_work_dep_guidance.py` — single-concern, follows existing naming convention.

## 4. Recommendation (confidence: 0.90)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Test file | `test_start_work_dep_guidance.py` | Single-concern isolation |
| Setup | Copy `_make_board`/`_write_task` helpers (per convention) | All test files are self-contained |
| AC1 approach | Real filesystem deps | Natural, no mocks needed |
| AC2 approach | Real filesystem (no deps + archived dep) | Natural |
| AC3 approach | `patch.object(engine, "show_task", side_effect=...)` | Clean; tests each exception independently |
| Test class | One class per AC (`TestDepGuidanceBlocked`, `TestDepGuidanceNoDeps`, `TestDepGuidanceResilience`) | Clear separation |

**Challenge:** FALLBACK — trivial test-writing research, challenger overkill for T1 scope.

## 5. Follow-up Tasks

No additional tasks needed — #1526 itself moves to backlog for test-writer pickup.
