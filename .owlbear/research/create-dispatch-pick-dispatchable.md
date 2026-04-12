# Create dispatch.py with pick_dispatchable()

> **Owning task:** #824 — Create dispatch.py with pick_dispatchable()
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Phase 3 of the kanban engine restructuring brief extracts dispatch logic from the MCP server layer (`server.py`) into a transport-free engine module (`dispatch.py`). The AC specifies `pick_dispatchable(engine, *, limit=25, tag="") → list[Task]` owning TDD/clarity gate predicates and priority/status rank maps.

**Key questions:** (1) What data access strategy avoids the body-stripping bug? (2) Should gate predicates be separate functions or inlined? (3) Are there any deviations between the two existing gate implementations?

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `serve/kanban/src/owlbear_kanban/engine.py` | .95 | `list_tasks()` reads full `Task` then converts to `TaskSummary`; `_tasks_dir` accessor |
| S2 | `serve/kanban/src/owlbear_kanban/models.py` | .95 | `TaskSummary` uses `extra="ignore"`, excludes `body` — gates can't use it |
| S3 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L323-405 | .95 | `_check_pick_gates`, rank maps, `pick_tasks` implementation |
| S4 | `serve/orchestrator/src/owlbear/planner/gates.py` | .90 | `check_tdd`, `check_clarity`, `check_gates` — typed `Task` params |
| S5 | `serve/orchestrator/src/owlbear/planner/selector.py` | .90 | `PRIORITY_RANK`, `STATUS_RANK`, `select_tasks()`, DISPATCH_CAP=20 |
| S6 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | .90 | Phase 3 spec, topology, rank-map rationale |
| S7 | `.owlbear/research/migrate-dispatcher-to-pick-tasks.md` | .85 | Prior art: gate-copy rationale, body-stripping note |
| S8 | `tests/test_pick_tasks.py` + `tests/test_kanban_mcp_migration.py` | .80 | Existing MCP-level tests; mock patterns |

## 3. Analysis

### 3.1 Gate Implementation Comparison

| Aspect | MCP server (S3) | Orchestrator planner (S4) | Delta |
|--------|-----------------|---------------------------|-------|
| Input type | `dict` | `Task` (Pydantic) | Type difference only |
| TDD gate | Identical logic | Identical logic | None |
| Clarity gate | Identical logic | Identical logic | None |
| AC regex | `r"(?m)^\s*(-\s\|\d+\.\s)"` | Same | None |
| Non-impl tags | 9-item frozenset | Same 9-item frozenset | None |
| Clarity statuses | `{todo, in-progress, review, docs, done}` | Same | None |
| Priority ranks | critical=0..someday=4 | Same | None |
| Status ranks | done=0..research=6 | Same | None |

**Verdict: Implementations are identical.** The engine `dispatch.py` consolidates them into one canonical location.

### 3.2 Body-Stripping Bug (discovery)

Current MCP `pick_tasks` calls `engine.list_tasks()` → returns `TaskSummary` (body excluded via `extra="ignore"`) → gates check `body=""` for all tasks. **All active-status tasks fail clarity gate** because empty body has no bullet/numbered items. The MCP tests pass because mocks return `TaskRecord` (has body) or patch `_run_kanban` with raw JSON (has body).

**Impact:** `pick_dispatchable()` MUST read full `Task` objects, not `TaskSummary`. This also fixes the MCP tool when the adapter is slimmed to call `pick_dispatchable()`.

### 3.3 Data Access Strategy

| Option | Approach | Correctness | Coupling |
|--------|----------|:-----------:|:--------:|
| A. Read from `engine._tasks_dir` | Use `task_io.read_task` + glob (same pattern as `list_tasks`) | Correct — full `Task` with body | Package-internal |
| B. New `engine._list_full_tasks()` | Add helper method to engine | Correct | Cleaner, but modifies engine.py |
| C. Accept `list[Task]` param | Caller provides tasks | Correct | Decoupled, but shifts responsibility |

**Recommendation (.88): Option A.** `dispatch.py` is in the same package; `_tasks_dir` access is package-private convention. Matches the established pattern in `engine.list_tasks()`. Option B adds a method to engine.py not required by the AC. Option C changes the specified signature.

### 3.4 Gate Structure

| Option | Structure | Testability | LOC |
|--------|-----------|:-----------:|:---:|
| A. Separate functions | `check_tdd_gate(task)`, `check_clarity_gate(task)` | Individual gate testing | ~40 |
| B. Single composite | `_check_gates(task)` | Composite only | ~20 |

**Recommendation (.85): Option A.** The AC says "Owns gate predicates" (plural). Separate functions match the orchestrator pattern (S4). #823 tests verify each gate independently.

## 4. Recommendation (.88 confidence)

Extract to `serve/kanban/src/owlbear_kanban/dispatch.py`:

1. **Two gate functions** — `check_tdd_gate(task: Task) -> bool`, `check_clarity_gate(task: Task) -> bool`
2. **Rank maps as module constants** — `PRIORITY_RANK`, `STATUS_RANK` with docstring noting execution priority ≠ display order
3. **`pick_dispatchable(engine, *, limit=25, tag="")`** — reads full `Task` from `engine._tasks_dir`, filters (unblocked + unclaimed + tag), applies gates, sorts by rank tuple, caps at limit
4. **Non-impl tags + clarity statuses + AC regex** as module-level frozensets/compiled pattern

**MCP adapter change** (separate task scope): `pick_tasks` in server.py becomes thin wrapper — calls `pick_dispatchable()`, converts `Task` → `KanbanTask`, formats dispatch response.

Challenge: N/A — T1 extraction of pre-existing logic; no new capability, no architecture/security/breaking change.

## 5. Follow-up Tasks

- #823 (RED tests) must complete first — #824 depends on it
- Body-stripping bug in MCP `pick_tasks` is implicitly fixed when adapter calls `pick_dispatchable()`
- No additional follow-up tasks needed — existing decomposition is complete
