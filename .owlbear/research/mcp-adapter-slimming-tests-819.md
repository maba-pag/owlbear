# MCP Adapter Slimming Regression Tests

> **Owning task:** #819 — Tests — MCP adapter slimming regression
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Task #819 provides regression tests ensuring the mcp-kanban adapter stays thin after the Phase 2 engine extraction (#818). The tests guard three boundaries: no engine files in mcp-kanban, all 8 MCP tools work via the extracted `owlbear_kanban` package, and `server.py` creates `KanbanEngine` from that package.

**Key finding:** #818 already completed the extraction AND slimming — engine files were moved, imports were updated, and mcp-kanban's `pyproject.toml` now depends on `owlbear-kanban`. The current mcp-kanban src dir contains only: `server.py`, `models.py`, `__init__.py`, `__main__.py`. So these tests pass GREEN against the current codebase. RED verification is conceptual (tests would have failed before #818).

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | Codebase | 1.0 — imports, 8 tools, lifespan |
| S2 | `serve/kanban/src/owlbear_kanban/__init__.py` | Codebase | 0.9 — canonical exports |
| S3 | `tests/test_engine_package_boundary_817.py` | Codebase | 0.9 — AST import checking pattern |
| S4 | `tests/test_kanban_mcp_migration.py` | Codebase | 0.8 — MCP tool mock testing pattern |
| S5 | `serve/mcp-kanban/pyproject.toml` | Codebase | 0.8 — dependency declaration |
| S6 | Task #818 body (builder + review notes) | Kanban | 0.9 — extraction details, stale import findings |
| S7 | `tests/test_remove_legacy_engine_models_831.py` | Codebase | 0.7 — file-absence check pattern |

## 3. Analysis

### 3.1 Current Adapter State

| File | Present | Purpose |
|------|---------|---------|
| `server.py` | Yes | 8 MCP tools, thin wrappers over `KanbanEngine` |
| `models.py` | Yes | `KanbanTask` boundary model |
| `__init__.py` | Yes | Package marker |
| `__main__.py` | Yes | Entry point |
| `engine.py` | **No** | Moved to `owlbear_kanban` |
| `engine_models.py` | **No** | Deleted (was missed in initial #818, fixed since) |
| `task_io.py` | **No** | Moved to `owlbear_kanban` |
| `config_loader.py` | **No** | Moved to `owlbear_kanban` |
| `activity_log.py` | **No** | Moved to `owlbear_kanban` |
| `agent_names.py` | **No** | Moved to `owlbear_kanban` |

### 3.2 Test Approach Comparison

| Approach | Boundary | Functional | Complexity | Duplication |
|----------|----------|------------|------------|-------------|
| **A: Pure boundary** | AST + file absence | None | Low | Low |
| **B: Boundary + mock tools** | AST + file absence | Mock engine, verify delegation | Medium | Low |
| **C: Boundary + integration** | AST + file absence | Temp board, full roundtrip | High | Medium (overlaps existing tool tests) |

### 3.3 The 8 MCP Tools and Return Types

| Tool | Returns | Engine Method |
|------|---------|---------------|
| `list_tasks` | `list[TaskSummary]` | `engine.list_tasks()` |
| `show_task` | `KanbanTask` | `engine.show_task()` |
| `create_task` | `KanbanTask` | `engine.create_task()` |
| `move_task` | `KanbanTask` | `engine.move_task()` |
| `edit_task` | `KanbanTask` | `engine.edit_task()` |
| `start_work` | `KanbanTask` | `engine.start_work()` |
| `end_work` | `KanbanTask` | `engine.end_work()` |
| `pick_tasks` | `dict` (`dispatch` list) | `engine.list_tasks()` + gate filtering |

### 3.4 Stale Import Finding

4 test files still import from the old `owlbear_mcp_kanban.engine*` paths (broken since #818):
- `test_kanban_mcp_migration.py` — `from owlbear_mcp_kanban.engine`
- `test_kanban_engine_roundtrip.py` — `.engine`, `.config_loader`, `.task_io`
- `test_kanban_task_io.py` — `from owlbear_mcp_kanban.task_io`
- `test_rename_archive_dir_744.py` — `from owlbear_mcp_kanban.engine`

These have `# type: ignore[import-not-found]` markers but will fail at runtime. Not in #819 scope — tracked as separate concern for #822 (migrate all workspace imports).

## 4. Recommendation

**Approach B: Boundary + mock-based tool verification** (confidence: 0.85)

Three `TestFromAC` classes in `tests/test_mcp_adapter_slimming_819.py`:

1. **`TestFromAC_AdapterImportBoundary` (AC1):** 6 engine file absence checks + AST import verification confirming `server.py` imports from `owlbear_kanban` and NOT from `owlbear_mcp_kanban.engine*`.

2. **`TestFromAC_AllToolsWork` (AC2):** Parametrized mock-based tests — mock `KanbanEngine` on `AppContext`, call each of 8 tool functions, verify correct engine method called and correct return type. Avoids temp board complexity; doesn't duplicate existing per-feature tests.

3. **`TestFromAC_EngineCreation` (AC3):** Test `app_lifespan` yields `AppContext` with a `KanbanEngine` instance whose type matches `owlbear_kanban.KanbanEngine`.

**RED verification (AC4):** Since #818 is already merged, RED is conceptual. Each test should include a diagnostic message explaining what pre-slimming state would cause failure.

Challenge: FALLBACK — subagent not available in researcher mode.

## 5. Follow-up Tasks

- No additional follow-up tasks needed — #819 IS the implementation task, advancing to backlog.
- Stale test imports covered by existing #822 scope.
