# Slim server pick_tasks to thin wrapper

> **Owning task:** #826 — Slim server pick_tasks to thin wrapper
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Phase 3, step 4 (final task). After #824 creates `dispatch.py` with `pick_dispatchable()`, server.py's `pick_tasks` must become a thin wrapper: delegate to `pick_dispatchable`, remove all inline gating logic, preserve the response format and MCP contract.

**Questions:** (1) What exact lines change in server.py? (2) Which existing tests break and how should the builder handle them? (3) Does `import re` survive? (4) Any risk from the boundary conversion AC line?

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L326-405 | .95 | Current inline implementation: 8 `_PICK_*` symbols + `_check_pick_gates` + inline sort/cap/format |
| S2 | `tests/test_server_pick_tasks_thin_wrapper_825.py` | .95 | 14 RED/PASS tests defining thin wrapper contract (AC1-AC4) |
| S3 | `.owlbear/research/server-pick-tasks-thin-wrapper-tests.md` | .90 | #825 research: mock strategy, test categorization, RED failure modes |
| S4 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` Phase 3 | .90 | O3: pick_dispatchable importable without MCP; server is thin adapter |
| S5 | `tests/test_kanban_mcp_migration.py` L595-660, L816-840 | .85 | Pick_tasks migration tests — 5 tests assert engine.list_tasks delegation |
| S6 | `tests/test_mcp_adapter_slimming_819.py` L277-291 | .85 | Adapter test asserts engine.list_tasks delegation |
| S7 | `tests/test_pick_tasks.py` | .70 | 38 legacy tests all broken (stale `kanban_bin` AppContext pattern) |
| S8 | `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` | .80 | KanbanTask boundary model with `_coerce_claimed` validator |

## 3. Analysis

### 3.1 Implementation Change Matrix

| Component | Remove | Add | Lines affected |
|-----------|--------|-----|:--------------:|
| `import re` | Yes — sole consumer is `_PICK_AC_PATTERN` | — | L5 |
| `_PICK_AC_PATTERN` | Yes | — | L329 |
| `_PICK_CLARITY_STATUSES` | Yes | — | L330 |
| `_PICK_NON_IMPL_TAGS` | Yes | — | L331-343 |
| `_PICK_PRIORITY_RANK` | Yes | — | L345-351 |
| `_PICK_STATUS_RANK` | Yes | — | L352-360 |
| `_PICK_MAX_PRIORITY_RANK` | Yes | — | L361 |
| `_PICK_MAX_STATUS_RANK` | Yes | — | L362 |
| `_check_pick_gates()` | Yes | — | L365-374 |
| `pick_tasks` body | Replace inline logic | 3-line delegation | L383-405 |
| Import line | — | `from owlbear_kanban.dispatch import pick_dispatchable` | Top of file |

**None of the 8 removed symbols are in `__all__`.** No public API impact.

### 3.2 Thin Wrapper Implementation

```python
# After refactoring, pick_tasks body becomes:
app_ctx: AppContext = ctx.request_context.lifespan_context
tasks = pick_dispatchable(app_ctx.engine, limit=limit, tag=tag)
return {"dispatch": [{"task_id": t.id, "status": t.status} for t in tasks]}
```

Decorator, signature, docstring, and return type unchanged. MCP contract preserved.

### 3.3 Boundary Conversion AC Line

AC says "Boundary conversion from `Task` to `KanbanTask` happens in server." Current `pick_tasks` does NOT return `KanbanTask` — it returns `{"dispatch": [...]}` with primitive fields. This AC line describes the **principle** that the server layer owns model conversion, not a new format requirement. The dispatch dict format stays as-is.

If a future consumer needs full `KanbanTask` output, the conversion point is already established (see `_record_to_task` helper pattern used by all other tools).

### 3.4 Existing Test Impact Analysis

| Test file | Tests | Current status | Impact after #826 | Builder action |
|-----------|:-----:|:--------------:|-------------------|----|
| `test_server_pick_tasks_thin_wrapper_825.py` AC1 (4) | 4 | RED | **GREEN** — import resolves, delegation works | None — this is the target |
| `test_server_pick_tasks_thin_wrapper_825.py` AC2 (3) | 3 | RED | **GREEN** — symbols removed | None — this is the target |
| `test_server_pick_tasks_thin_wrapper_825.py` AC3 (4) | 4 | PASS | **BREAK** — mock at engine.list_tasks, but pick_tasks no longer calls it | Patch `pick_dispatchable` to return Task lists |
| `test_server_pick_tasks_thin_wrapper_825.py` AC4 (3) | 3 | PASS | **PASS** — MCP registration unchanged | None |
| `test_kanban_mcp_migration.py` TestFromAC_PickTasks (5) | 5 | PASS | **BREAK** — assert engine.list_tasks delegation | Superseded by #825 AC1; update to mock pick_dispatchable |
| `test_mcp_adapter_slimming_819.py` pick_tasks (1) | 1 | PASS | **BREAK** — asserts engine.list_tasks called | Superseded by #825 AC1; update to mock pick_dispatchable |
| `test_pick_tasks.py` (38) | 38 | BROKEN | Already broken (stale `kanban_bin`) | Not #826's scope — separate cleanup |

**Summary:** 6 currently-passing tests will break. All are superseded by #825 delegation tests. Builder must update their mock strategy as part of GREEN.

### 3.5 Implementation Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|:-----:|
| A. Direct delegation + mock updates | Replace body, remove symbols, update 6 broken tests to mock pick_dispatchable | Minimal diff, all tests pass | ~30 LOC test changes | **.90** |
| B. Direct delegation only | Replace body, remove symbols, leave broken tests | Smallest diff | 6 test failures violate AC6 (O4) | .50 |
| C. Adapter indirection | Add `_pick_tasks_impl` wrapper layer | Over-engineered, unnecessary abstraction | YAGNI violation | .30 |

## 4. Recommendation

**Option A** — direct delegation with mock updates. Confidence: **0.90**.

The refactoring is mechanical: remove 8 symbols, add 1 import, replace 20 lines of inline logic with 3 lines of delegation. The builder must also update 6 superseded tests (mock `pick_dispatchable` instead of `engine.list_tasks`). Total diff: ~50 LOC removed from server.py, ~30 LOC test mock updates.

**Blocker:** #824 (dispatch.py) must be complete first. Currently in-progress.

**Key guidance for builder:**
- `import re` can be removed — no other consumer in server.py
- AC3 tests from #825 need `patch("owlbear_mcp_kanban.server.pick_dispatchable")` added to provide test data
- Migration tests in `test_kanban_mcp_migration.py` and `test_mcp_adapter_slimming_819.py` are superseded but must still pass — update mock target from `engine.list_tasks` to `pick_dispatchable`
- The AC "boundary conversion" line is a principle, not a format change

Challenge: FALLBACK — challenger subagent not available.

## 5. Follow-up Tasks

- Follow-up #1: Clean up stale `test_pick_tasks.py` — 38 tests broken by Phase 2 `kanban_bin` → engine migration. Pre-existing issue, not caused by #826.
