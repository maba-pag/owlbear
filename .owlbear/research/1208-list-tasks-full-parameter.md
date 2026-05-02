# list_tasks full=True Parameter — Validity Check

> **Owning task:** #1208 — Add full=True parameter to list_tasks to avoid body re-reads
> **Date:** 2026-05-02 **Status:** Complete — INVALID PREMISE

## 1. Context and Question

Task #1208 proposes adding `full: bool = False` to `list_tasks()` so callers needing body (claimed: `pick_tasks`, `dispatch`) avoid "re-reads". Architecture review rejected the premise. This research validates the rejection.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` — `list_tasks()` L584, cache L404, projection L751-761 | 1.0 |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` — `pick_tasks()` L2217 | 1.0 |
| 3 | `serve/kanban/src/owlbear_kanban/dispatch.py` — `pick_dispatchable()` L137 | 1.0 |
| 4 | `serve/kanban/src/owlbear_kanban/models.py` — `TaskSummary` L463, `TaskFull` L576 | 1.0 |

## 3. Analysis

### Claim 1: "body re-reads" exist → FALSE

`_task_cache: dict[str, tuple[int, Task]]` stores full `Task` objects keyed by mtime. The `TaskSummary` conversion at L751-761 is `model_dump()` → `model_validate()` — an in-memory Pydantic projection, not disk I/O. Cost: ~microseconds per task.

### Claim 2: `pick_tasks` needs body → FALSE

`pick_tasks()` accesses only: `dep_status`, `status`, `id`, `priority`, `title`, `tags`. Zero body reads.

### Claim 3: `dispatch` would use full=True → FALSE

`pick_dispatchable()` bypasses `list_tasks()` entirely — it iterates `engine._tasks_dir.glob("*.md")` and calls `engine.show_task()` per file. Even if `list_tasks` returned body, dispatch wouldn't use it.

### Claim 4: TaskFull already covers this → TRUE

`TaskFull(TaskSummary)` at models.py L576 adds `body` and `created` back. If a future caller needed body-inclusive listing, it could be returned as `list[TaskFull]` — no new parameter needed.

### Trade-Off Matrix

| Option | Benefit | Cost | YAGNI? | Confidence |
|--------|---------|------|--------|------------|
| Implement full=True | None (no caller needs it) | API surface growth, dual return type | Yes | N/A |
| Close task as invalid | Removes speculative work | None | — | 0.95 |
| Rearchitect dispatch to use list_tasks | Reduces N+1 in dispatch | Dispatch needs body for gates; list projection would need rework | Premature | 0.40 |

## 4. Recommendation

**Close this task.** Confidence: 0.95.

The premise is factually wrong on all three pillars: (a) no disk re-reads occur, (b) neither named consumer needs body from `list_tasks`, (c) the third-party pattern (`TaskFull`) already exists if needed in the future. YAGNI applies.

**Dependency fix:** Remove `1208` from #1209's `depends_on` — it validates dispatch constants vs config, which has no relationship to a `full` parameter.

## 5. Follow-up Tasks

None needed. The "real" performance concern (dispatch N+1 `show_task()`) is already scoped as #1214.

## Challenge Results

Architecture review already served as challenger (confidence in original: 0.38). Researcher concurs with rejection — all 5 rejection reasons validated against live code.
