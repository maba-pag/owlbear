# Remove Compat Alias + Migrate All Workspace Imports

> **Owning task:** #822 — Remove compat alias + migrate all workspace imports
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Phase 2 step 6 (final). The `TaskRecord = Task` compat alias in `owlbear_kanban.models`
was introduced during Phase 2 step 1 (rename). Now that the engine package is extracted,
all consumers must migrate to `Task` and the alias must be removed. Additionally, several
test files still import engine symbols from the old `owlbear_mcp_kanban` namespace.

**Question:** What is the full scope of changes, and are there any non-obvious risks?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/models.py` | Codebase | 1.0 — alias definition |
| S2 | `serve/kanban/src/owlbear_kanban/__init__.py` | Codebase | 1.0 — re-export |
| S3 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | Codebase | 1.0 — runtime consumer |
| S4 | `tests/test_kanban_engine_*.py` (4 files) | Codebase | 1.0 — test imports |
| S5 | `tests/test_kanban_mcp_migration.py` | Codebase | 1.0 — test imports |
| S6 | `tests/test_kanban_task_io.py` | Codebase | 1.0 — test + stale import |
| S7 | Brief `draft-kanban-web-gui-prep/brief.md` | Design doc | 0.9 — defines approach |

## 3. Analysis — Change Inventory

### 3a. Alias deletion (owlbear_kanban package)

| File | Lines | Change |
|------|-------|--------|
| `models.py` | 5, 89-90 | Remove alias + docstring line |
| `__init__.py` | 9, 15 | Remove `TaskRecord` from import + `__all__` |

### 3b. TaskRecord to Task migration (symbol rename)

| File | Import changes | Usage changes | Total |
|------|---------------|---------------|-------|
| `server.py` (MCP) | 1 (TYPE_CHECKING) | 2 (function sig + docstring) | 3 |
| `engine.py` (docstrings only) | 0 | 7 | 7 |
| `task_io.py` (docstrings only) | 0 | 4 | 4 |
| `test_kanban_engine_crud.py` | 1 | ~8 | ~9 |
| `test_kanban_engine_listing.py` | 1 | 2 | 3 |
| `test_kanban_engine_models.py` | 1 | ~30 (incl. class name) | ~31 |
| `test_kanban_task_io.py` | 1 | 2 | 3 |
| `test_kanban_mcp_migration.py` | 1 | ~15 | ~16 |
| `test_kanban_engine_compound.py` | 0 (docstrings) | 4 | 4 |
| `test_kanban_engine_roundtrip.py` | 0 (docstrings) | 3 | 3 |

### 3c. Stale owlbear_mcp_kanban imports (need owlbear_kanban)

| File | Current import | Target import |
|------|---------------|---------------|
| `test_kanban_engine_roundtrip.py` | `owlbear_mcp_kanban.{config_loader,engine,task_io}` | `owlbear_kanban.{config_loader,engine,task_io}` |
| `test_kanban_mcp_migration.py` | `owlbear_mcp_kanban.engine` | `owlbear_kanban` |
| `test_kanban_task_io.py` | `owlbear_mcp_kanban.task_io` | `owlbear_kanban.task_io` |
| `test_rename_archive_dir_744.py` | `owlbear_mcp_kanban.engine` | `owlbear_kanban.engine` |

### 3d. Risk assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Missed reference breaks import | Low | `grep -r TaskRecord` verification (AC) |
| Stale `type: ignore` comments after fix | Low | Remove alongside import migration |
| `TestFromAC_TaskRecord` class rename | Low | Rename to `TestFromAC_Task` for consistency |
| Docstring-only changes cause no test failure | None | #821 tests grep for `TaskRecord` in source |

## 4. Recommendation

**Approach:** Mechanical find-and-replace in two passes:
1. Migrate all `TaskRecord` references to `Task` across all files
2. Migrate all `owlbear_mcp_kanban.{engine,task_io,config_loader}` imports to `owlbear_kanban`
3. Remove the alias definition and re-export
4. Run full test suite + `grep -r TaskRecord` verification

**Confidence: .95** — purely mechanical refactor with no behavioral change. Every site
is cataloged above. The #821 RED tests provide a safety net.

**Tier: T1 (autonomous)** — refactor, no new capability, no architecture change.

Challenge: FALLBACK — trivial mechanical refactor, challenge skipped per Step 3.5 rule.

## 5. Follow-up Tasks

Task #822 itself is the implementation task. No additional follow-up tasks needed —
the AC is complete and self-contained. #821 provides the RED tests.
