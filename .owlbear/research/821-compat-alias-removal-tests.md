# Tests — Compat Alias Removal + Import Migration

> **Owning task:** #821 — Tests — Compat alias removal + import migration
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Phase 2 step 5 (TDD RED). Write tests that verify the compat alias is removed and all
imports are migrated. Tests must fail RED now and pass GREEN after #822 completes the
mechanical migration. **Question:** What test patterns, grep scope, and exclusions produce
accurate RED coverage for the 4 ACs?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/` (5 .py files) | Codebase | 1.0 — alias definition + docstring refs |
| S2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | Codebase | 1.0 — TYPE_CHECKING import |
| S3 | `tests/test_rename_taskrecord_to_task_800.py` | Codebase | 1.0 — pattern reference (AST + string grep) |
| S4 | `tests/test_engine_package_boundary_817.py` | Codebase | 0.9 — pattern reference (rglob + AST) |
| S5 | `.owlbear/research/822-remove-compat-alias-migrate-imports.md` | Research doc | 1.0 — full change inventory |
| S6 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | Design doc | 0.9 — phase sequencing |
| S7 | 9 test files with TaskRecord refs (see §3a) | Codebase | 1.0 — grep targets |

## 3. Analysis

### 3a. TaskRecord Reference Inventory

| Location | Refs | Type | RED trigger |
|----------|------|------|-------------|
| `models.py` (engine) | 3 | Alias def + docstring + comment | AC1 |
| `__init__.py` (engine) | 2 | Import + `__all__` entry | AC1 |
| `engine.py` (engine) | 8 | Docstring `:class:\`TaskRecord\`` | AC1 |
| `task_io.py` (engine) | 4 | Docstring `:class:\`TaskRecord\`` | AC1 |
| `server.py` (MCP) | 3 | TYPE_CHECKING import + sig + docstring | AC1, AC2 |
| `test_kanban_engine_models.py` | ~36 | Import + code + docstrings | AC1, AC3 |
| `test_kanban_mcp_migration.py` | ~15 | Import + code + docstrings | AC1, AC3 |
| `test_kanban_engine_crud.py` | ~8 | Import + code + docstrings | AC1, AC3 |
| `test_kanban_task_io.py` | ~10 | Import + code + docstrings | AC1, AC3 |
| `test_kanban_engine_listing.py` | ~4 | Import + local import + docstrings | AC1, AC3 |
| `test_kanban_engine_compound.py` | 4 | Docstrings only | AC1 |
| `test_kanban_engine_roundtrip.py` | 3 | Docstrings only | AC1 |
| `test_rename_taskrecord_to_task_799.py` | 12 | Import + code + docstrings | AC1, AC3 |
| `test_rename_taskrecord_to_task_800.py` | ~15 | String literals in assertions | AC1 |
| **Total** | **~127** | | |

### 3b. Stale Namespace Imports (owlbear_mcp_kanban.{engine,task_io,config_loader})

| File | Stale import | Target |
|------|-------------|--------|
| `test_kanban_engine_roundtrip.py` | `owlbear_mcp_kanban.{config_loader,engine,task_io}` | `owlbear_kanban.*` |
| `test_kanban_mcp_migration.py` | `owlbear_mcp_kanban.engine` | `owlbear_kanban` |
| `test_kanban_task_io.py` | `owlbear_mcp_kanban.task_io` | `owlbear_kanban.task_io` |
| `test_rename_archive_dir_744.py` | `owlbear_mcp_kanban.engine` | `owlbear_kanban.engine` |

### 3c. Test Design — Approach Comparison

| Approach | Precision | Complexity | Docstring coverage |
|----------|-----------|------------|-------------------|
| A: AST-only (import inspection) | High | Medium | None — misses docstrings |
| B: String grep only | Medium | Low | Full |
| C: Hybrid (AST for imports + string for refs) | **High** | Medium | **Full** |

**Recommendation: Approach C (hybrid)** — matches #800/#817 patterns already in the codebase.

### 3d. Scope Boundaries

| Scope | Include | Exclude |
|-------|---------|---------|
| Engine source | `serve/kanban/src/**/*.py` | `__pycache__/` |
| MCP adapter source | `serve/mcp-kanban/src/**/*.py` | `__pycache__/` |
| Test files | `tests/**/*.py` | `__pycache__/`, self (`test_compat_alias_removal_821.py`) |
| NOT included | `.owlbear/`, briefs, research docs, `.md` files | — |

Self-exclusion is required because the test file itself references `TaskRecord` in
assertion messages, docstrings, and class names.

### 3e. Test Classes Mapped to ACs

| Class | AC | Tests (RED count) | RED reason |
|-------|----|--------------------|------------|
| `TestFromAC_NoTaskRecordReferences` | AC1 | 3 | Engine: 17 refs, MCP: 3 refs, tests: ~90 refs |
| `TestFromAC_EngineImportsOwlbearKanban` | AC2 | 2 | server.py TYPE_CHECKING imports TaskRecord; 4 test files use stale namespace |
| `TestFromAC_TestFileImports` | AC3 | 2 | 7 test files import TaskRecord from owlbear_kanban.models |
| _AC4 meta-criterion_ | AC4 | 0 | Satisfied by all tests failing RED |

**Estimated test count: 7 tests, all RED.**

## 4. Recommendation

**Single test file:** `tests/test_compat_alias_removal_821.py` with 3 classes, 7 tests.
Hybrid AST + string grep. Self-exclusion via `Path(__file__)` comparison.

**Confidence: .92** — Well-defined TDD RED task. Patterns established by #800 and #817.
Only risk is edge-case grep false positives in assertion string literals (mitigated by
self-exclusion and the fact that #822's migration must also update those files).

**Tier: T1** — test implementation, no architectural decisions.

Challenge: FALLBACK — trivial TDD RED task with established patterns, skipped per Step 3.5.

## 5. Follow-up Tasks

None needed — #822 (GREEN phase) already exists at backlog, depends on #821.
