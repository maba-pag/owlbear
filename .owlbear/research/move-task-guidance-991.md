# Wire Guidance into `move_task` with Forward-Skip Detection

> **Owning task:** #991 — Wire guidance into `move_task` with forward-skip detection
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #991 is a subtask of #973 (Block-Time Guidance from owlbear-kanban MCP). All decisions locked in Brief (D1–D9) via 3-round architect debate. This research validates the implementation path for wiring `collect_guidance` into the MCP `move_task` tool with pre-read for forward-skip detection.

Questions: (1) How does `move_task` capture "before" state for skip detection? (2) How is `status_names` extracted for the guidance call? (3) What are the TOCTOU implications?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L210–223 | Codebase | .95 — current `move_task` handler |
| S2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L161–168 | Codebase | .95 — `_show_validated()` helper for pre-read |
| S3 | `serve/kanban/src/owlbear_kanban/engine.py` L712–765 | Codebase | .95 — engine `move_task` returns updated Task |
| S4 | `serve/kanban/src/owlbear_kanban/engine.py` L303–309 | Codebase | .90 — `board_config()` returns deep copy with `statuses` list |
| S5 | `.owlbear/briefs/draft-blocked-task-dr-enforcement/decisions.md` D2, D6 | Codebase | .95 — locked decisions for forward-skip + status ordering |
| S6 | `.owlbear/research/edit-task-guidance-985.md` | Codebase | .90 — sibling guidance wiring pattern (try/except wrapper) |
| S7 | `.owlbear/research/guidance-module-987.md` §3.2 | Codebase | .90 — forward-skip predicate logic and `status_names` kwarg |

## 3. Analysis

### 3.1 Pre-Read Pattern (S1, S2, D6)

`move_task` is the only guidance integration that requires a `before` state (siblings #985/#989 pass `before=None`). The existing `_show_validated()` helper (S2) retrieves a task and returns a validated `KanbanTask` — exactly what's needed.

Pre-read must happen **before** the `engine.move_task()` call to capture the task's current status. TOCTOU risk (status changes between pre-read and engine call) acknowledged and accepted by Brief R1.4 and architect rebuttal C4 — guidance is advisory, not a gate.

### 3.2 Status Names Extraction (S4, S7, D6)

`board_config().statuses` returns a list of dicts, each with a `"name"` key. Extract via `[s["name"] for s in app_ctx.engine.board_config().statuses]`. This list never includes `"archived"` (archived is a filesystem concept, not a status column), so archived moves are automatically excluded from forward-skip detection.

### 3.3 Implementation Sketch (~15 lines of change)

```python
before = await _show_validated(app_ctx, str(task_id))
# ... existing engine call ...
task = _record_to_task(record)
try:
    status_names = [s["name"] for s in app_ctx.engine.board_config().statuses]
    task.guidance = collect_guidance(
        "move",
        before=before,
        after=task,
        status_names=status_names,
    )
except Exception:  # noqa: BLE001
    pass  # Guidance failure must not break the operation
return task
```

### 3.4 Comparison with Siblings

| Aspect | `edit_task` (#985) | `end_work` (#989) | `move_task` (#991) |
|--------|-------------------|-------------------|--------------------|
| Pre-read needed | No (`before=None`) | No (`before=None`) | Yes (`_show_validated`) |
| Extra kwargs | None | `outcome=outcome` | `status_names=[...]` |
| Tag removal | `block:user` in same call | `block:user` sequential | None |
| `asyncio.to_thread` | One call | Two calls (block path) | One call |
| Lines of change | ~15 | ~20 | ~15 |

### 3.5 Test Strategy

Integration tests using `KanbanEngine` with `tmp_path` fixture (proven pattern in `test_tool_annotations_494.py` and `test_cockpit_mutation_api.py`). One test per AC case:

| Test | Setup | Move | Expected |
|------|-------|------|----------|
| Forward skip > 1 | Task at `research` | → `in-progress` (skip 2) | Guidance with skip message |
| Adjacent 1-slot | Task at `todo` | → `in-progress` (skip 0) | Empty guidance |
| Backward move | Task at `review` | → `todo` | Empty guidance |
| Archived | Task at `todo` | → `archived` | Empty guidance |

Tests need a real engine to exercise the full `move_task` → `board_config` → `collect_guidance` path.

### 3.6 Dependency Status

| Dep | Task | Status | Blocks #991? |
|-----|------|--------|-------------|
| #986 | `KanbanTask.guidance` field | backlog | Yes — field must exist for `task.guidance = ...` |
| #987 | `guidance.py` module | backlog | Yes — `collect_guidance` must exist for import |

Both at `backlog`. Task #991 `depends_on` should be wired to [986, 987].

### 3.7 Confidence Assessment

| Aspect | Confidence | Note |
|--------|-----------|------|
| Pre-read via `_show_validated` | .95 | Existing helper, established pattern |
| Status names extraction | .95 | `board_config()` is public, statuses list validated |
| TOCTOU acceptance | .90 | Brief R1.4, architect C4 rebuttal |
| Guidance wiring | .95 | Pattern proven by sibling #985 research |
| Test strategy | .90 | Engine fixture pattern from existing tests |
| Overall | .92 | |

## 4. Recommendation

Proceed with implementation per Brief Path A1 and locked decisions D2, D6. Implementation is ~15 lines of changes to `move_task` handler (pre-read, guidance import, try/except wrapper). Wire `depends_on` to [986, 987] before advancing.

Confidence: .92

Challenge: SKIPPED — approach locked via parent Brief 3-round architect debate with 9 decisions. No new recommendation to challenge; implementation path identical to validated siblings.

## 5. Follow-up Tasks

No new follow-up tasks — #991 is already atomic with clear AC. Dependencies #986 and #987 exist and are at backlog.
