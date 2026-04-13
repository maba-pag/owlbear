# Engine Package Boundary + Public API Tests

> **Owning task:** #817 — Tests — Engine package boundary + public API
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Phase 2 of the kanban engine restructuring (#798) extracts a standalone `owlbear_kanban` package from `serve/mcp-kanban/`. Task #817 writes RED tests that define the target boundary and API surface _before_ extraction. #818 (GREEN) depends on #817.

**Question:** What test structure, patterns, and assertions fully cover the 5 AC items while producing clean RED → GREEN signals?

## 2. Sources Studied

| Source | URL | Relevance | Score |
|--------|-----|-----------|-------|
| Existing `test_package_boundary.py` | workspace: `tests/test_package_boundary.py` | AST scanning pattern, ALLOWED_IMPORTS map, manifest guard | 1.0 |
| Current `engine.py` | workspace: `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` | Baseline KanbanEngine public methods to verify | 1.0 |
| Current `engine_models.py` | workspace: `serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py` | Task/TaskSummary/BoardConfig export targets | 1.0 |
| Brief | workspace: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | Target package topology, `__init__.py` exports | 0.9 |
| Phase 1 dependency tasks (#802-816) | kanban board | Phase 1 adds methods (board_config, refresh_config, valid_transitions, revision) that become part of public API | 0.8 |

## 3. Analysis

### 3.1 RED Mechanism Per AC

| AC | RED Mechanism | GREEN Trigger |
|----|--------------|---------------|
| AC1: `from owlbear_kanban import KanbanEngine, Task, TaskSummary` | ImportError — package doesn't exist | #818 creates `serve/kanban/` with exports |
| AC2: Engine doesn't import `mcp` or transport | `serve/kanban/` directory doesn't exist → assert fails | Directory created; files have no mcp imports |
| AC3: Public API surface | ImportError (same as AC1) | Import succeeds; methods/models present |
| AC4: MCP adapter imports `owlbear_kanban` | AST scan of `server.py` finds no `owlbear_kanban` → assert fails | #818 updates server.py imports |
| AC5: Tests fail RED before extraction | All above produce failures | All pass after extraction |

### 3.2 Test Structure

Single new file: `tests/test_engine_package_boundary_817.py` + ALLOWED_IMPORTS update in existing `test_package_boundary.py`.

| Test Class | AC | Tests | Pattern |
|------------|-----|-------|---------|
| `TestFromAC_EngineImportable` | AC1 | `test_import_core_exports` | Direct import |
| `TestFromAC_EngineBoundary` | AC2 | `test_engine_dir_exists`, `test_no_mcp_transport_imports` | Path check + AST scan |
| `TestFromAC_EnginePublicAPI` | AC3 | `test_engine_methods`, `test_boardconfig_exported` | Import + `hasattr` |
| `TestFromAC_AdapterImportsEngine` | AC4 | `test_adapter_imports_engine` | AST scan of `server.py` |

### 3.3 KanbanEngine Target Public API Surface

Methods present today + Phase 1 additions:

| Method/Property | Source | Phase |
|----------------|--------|-------|
| `list_tasks` | Current engine.py | Existing |
| `show_task` | Current engine.py | Existing |
| `create_task` | Current engine.py | Existing |
| `edit_task` | Current engine.py | Existing |
| `move_task` | Current engine.py | Existing |
| `claim_task` | Current engine.py | Existing |
| `release_task` | Current engine.py | Existing |
| `start_work` | Current engine.py | Existing |
| `end_work` | Current engine.py | Existing |
| `agent_name` (property) | Current engine.py | Existing |
| `board_config` | #806 | Phase 1 |
| `refresh_config` | #804 | Phase 1 |
| `valid_transitions` | #808 | Phase 1 |
| `revision` (property) | #810 | Phase 1 |

Exported models: `Task` (renamed from `TaskRecord`), `TaskSummary`, `BoardConfig`.

### 3.4 Interaction with `test_package_boundary.py`

The existing `ALLOWED_IMPORTS` map needs two changes:

1. Add `"owlbear_kanban": set()` — engine has no owlbear-namespace deps
2. Update `"owlbear_mcp_kanban": set()` → `"owlbear_mcp_kanban": {"owlbear_kanban"}` — adapter may import engine

These changes make the manifest guard fail RED (namespace not on disk). This is a complementary RED signal to the new test file.

### 3.5 Third-Party Import Boundary

The existing `test_package_boundary.py` only checks cross-owlbear-namespace imports. AC2 requires checking that `owlbear_kanban` does NOT import `mcp` or transport packages (third-party). The new test uses AST scanning with a transport-package blocklist: `{"mcp", "fastmcp"}`.

### 3.6 Dependency Note

All 8 Phase 1 deps (#802-816) are at `research` status. #817's RED tests don't require Phase 1 completion — they reference the _target_ interface (which fails with ImportError regardless). The dependency exists because #818 (GREEN) needs Phase 1 features before extraction.

## 4. Recommendation

**Approach:** New test file + ALLOWED_IMPORTS update, following existing AST-scanning conventions. Confidence: **0.90**.

Challenge: FALLBACK — Trivial recommendation following existing patterns; no alternative approaches to evaluate.

| Risk | Mitigation |
|------|------------|
| Phase 1 API additions not final | API surface test references brief's specified exports; any changes propagate through Phase 1 tasks |
| ALLOWED_IMPORTS update breaks manifest guard | Intentional RED — reviewed as part of #817 RED behavior |

## 5. Follow-up Tasks

No new follow-up tasks needed. #818 (Extract engine to serve/kanban/ + workspace config) already exists as the GREEN task and depends on #817.
