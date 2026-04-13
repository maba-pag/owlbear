# Tests — refresh_config + config staleness fix

> **Owning task:** #803 — Tests — refresh_config + config staleness fix
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Task #803 requests tests for `refresh_config()` and config staleness behavior in `KanbanEngine`. The key question: what test gaps exist, given that both the implementation and a related test file (`test_config_staleness_fix_828.py`) already exist?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` L106-113 | 1.0 | `refresh_config()` implementation — reloads config, updates `_config`, `_tasks_dir`, `_archive_dir` |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` L258-290 | 1.0 | `create_task()` already updates `self._config` after save (staleness fix in place) |
| 3 | `serve/kanban/src/owlbear_kanban/engine.py` L405-430 | 1.0 | `move_task()` validates `status` against `self._config.statuses` |
| 4 | `tests/test_config_staleness_fix_828.py` | 0.9 | Existing tests cover `create_task` staleness (next_id sync, tasks_dir update) |
| 5 | `serve/kanban/src/owlbear_kanban/engine.py` L86-91 | 0.8 | `_priority_rank()` and `_status_rank()` derive from `self._config` |
| 6 | `serve/kanban/src/owlbear_kanban/models.py` L42-57 | 0.7 | `BoardConfig` model: statuses, priorities, tasks_dir, next_id |

## 3. Analysis

### AC vs. existing coverage

| AC | Covered by existing tests? | Gap |
|----|---------------------------|-----|
| `refresh_config()` reloads YAML from disk | No | Needs dedicated tests |
| `refresh_config()` updates `_config`, tasks_dir, archive_dir, rank maps | No | Needs dedicated tests |
| `create_task` uses fresh config (staleness) | Yes — `test_config_staleness_fix_828.py` | DRY: skip, already covered |
| `refresh_config()` + `move_task` validates new statuses | No | Needs dedicated tests |
| Tests fail RED before implementation | N/A — impl already exists | Tests should PASS (GREEN) |

### Key observations

1. **Implementation precedes tests.** `refresh_config()` and the `create_task` staleness fix are already implemented. The "RED before implementation" AC is moot — tests will pass immediately.

2. **Overlap with #828.** `test_config_staleness_fix_828.py` already covers `create_task` updating `self._config` and `_tasks_dir`. Duplicating these tests violates DRY. Task #803 tests should focus on `refresh_config()` directly and its integration with `move_task`.

3. **Rank maps are untested.** `_priority_rank()` and `_status_rank()` are private methods derived from `self._config`. After `refresh_config()`, they should reflect new config. Testable via `board_config()` + `valid_transitions()` as public proxies.

### Proposed test structure

File: `tests/test_refresh_config_803.py`

| Test | AC | Approach |
|------|----|----------|
| `test_refresh_config_reloads_yaml_from_disk` | AC1 | Change next_id on disk → refresh → board_config().next_id updated |
| `test_refresh_config_updates_tasks_dir` | AC2 | Change tasks_dir on disk → refresh → verify via create_task targeting new dir |
| `test_refresh_config_updates_statuses` | AC2 | Add status on disk → refresh → valid_transitions includes it |
| `test_refresh_config_updates_priorities` | AC2 | Change priorities on disk → refresh → board_config().priorities updated |
| `test_refresh_config_then_move_task_accepts_new_status` | AC4 | Add status on disk → refresh → move_task succeeds |
| `test_refresh_config_then_move_task_rejects_removed_status` | AC4 | Remove status on disk → refresh → move_task raises ValueError |

## 4. Recommendation

**Write focused `refresh_config()` tests in a new file**, skipping create_task staleness tests (already covered by #828). Tests will be GREEN immediately since the implementation exists.

Confidence: **0.90** — straightforward test gap analysis with clear implementation to test against.

Challenge: FALLBACK — T1 trivial test task, challenger not invoked.

## 5. Follow-up Tasks

- Write `tests/test_refresh_config_803.py` with the 6 tests outlined above (at `todo` status, implementation-ready).
