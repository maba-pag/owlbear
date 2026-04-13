# Tests — Rename TaskRecord → Task

> **Owning task:** #799 — Tests — Rename TaskRecord → Task
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Phase 1, Chain 1 step 1 of the Kanban Engine Restructuring brief. The `TaskRecord` class in `engine_models.py` is the canonical engine model but its name doesn't match the brief's target name `Task`. This test task verifies the rename works with a backward-compatible alias.

**Question:** Can tests be written to verify (a) `Task` importable from `engine_models`, (b) `TaskRecord` alias identity, and (c) engine CRUD returns `Task` instances — all failing RED before implementation?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `engine_models.py` (line 59–87) | Codebase | 1.0 — defines current `TaskRecord` |
| S2 | `engine.py` (lines 29, 100–548) | Codebase | 1.0 — all CRUD methods return `TaskRecord` |
| S3 | Brief `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` Phase 1 table | Codebase | 0.9 — specifies rename + compat alias |
| S4 | Existing test patterns: `test_kanban_engine_models.py`, `test_kanban_engine_crud.py` | Codebase | 0.9 — established fixture/assertion patterns |

## 3. Analysis

### 3.1 Current State

- `TaskRecord` defined at `engine_models.py:59` with `ConfigDict(extra="allow")`
- Imported in 3 source modules + 6 test files
- No `Task` class exists in `owlbear_mcp_kanban` namespace
- Only other `Task` in workspace: `owlbear.planner.models.Task` (separate package, no collision)

### 3.2 Feasibility

| Criterion | Assessment |
|-----------|------------|
| Name collision | None — no `Task` in `owlbear_mcp_kanban` |
| Alias pattern | Standard Python: `TaskRecord = Task` after class definition |
| Test approach | Import `Task`, assert `TaskRecord is Task`, `isinstance` on CRUD returns |
| RED guarantee | `Task` not yet defined → `ImportError` on all tests |

### 3.3 Test File Structure

Target: `tests/test_rename_taskrecord_to_task_799.py`

| Test class | AC | Tests |
|------------|-----|-------|
| `TestFromAC_TaskImport` | AC1 | `Task` importable from `engine_models` |
| `TestFromAC_AliasIdentity` | AC2 | `TaskRecord is Task` (same object) |
| `TestFromAC_CrudReturnsTask` | AC3 | `create_task`, `edit_task`, `move_task`, `show_task`, `list_tasks` all return `Task` instances |

Reuses existing `_BASE_CONFIG_YAML` fixture pattern from `test_kanban_engine_crud.py`.

## 4. Recommendation

Proceed with test implementation as described. Confidence: **0.95**.

N/A — trivial rename. Challenge skipped per w-research: "skip for info-only or trivial research."

## 5. Follow-up Tasks

No additional follow-up tasks needed — #799 itself advances to backlog for the test-writer.
