# Retire Bookmark/Scope/Consolidation Dead Code from Knowledge Module

> **Owning task:** #1582 — Retire bookmark/scope/consolidation dead code from knowledge module
> **Date:** 2026-05-15 **Status:** Complete

## 1. Context and Question

Research #1576 classified bookmark, scope-transfer, consolidation, and copilot_auth
code as retire-targets with zero active callers. This task validates that classification
against current codebase state and identifies the precise implementation surface: which
files to delete, which lines to remove, and which tests need cleanup.

## 2. Sources Studied

| # | Source | Path | Relevance |
|---|--------|------|-----------|
| 1 | Research #1576 | `.owlbear/research/classify-inactive-knowledge-surfaces.md` | 1.0 |
| 2 | server.py (current) | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | 1.0 |
| 3 | knowledge `__init__.py` | `serve/knowledge/src/owlbear_knowledge/__init__.py` | 0.9 |
| 4 | knowledge `pyproject.toml` | `serve/knowledge/pyproject.toml` | 0.8 |
| 5 | Test files referencing retired symbols | `tests/`, `serve/mcp-knowledge/tests/` | 0.9 |

## 3. Analysis — Implementation Surface

### 3.1 Modules to Delete (5 files)

| Module | Active Callers | Confirmed Retire |
|--------|---------------|-----------------|
| `bookmark_pipeline.py` | 0 (lifespan wires, never called) | Yes |
| `bookmark_store.py` | 0 (lifespan wires, never called) | Yes |
| `consolidation.py` | 0 (no-op LLM stub wired but unused) | Yes |
| `copilot_auth.py` | 0 (not imported; token deleted on startup) | Yes |
| `scope_transfer.py` | 0 (imports in server.py feed dead tool functions) | Yes |

### 3.2 Server.py Changes

| Category | Items to Remove |
|----------|----------------|
| **Imports** | `BookmarkPipeline`, `BookmarkStore`, `ConsolidationService`, `TextCompletionFn`, `_do_import`, `export_scope`, `import_scope`, `resolve_global_db_path` |
| **Tool functions** | `bookmark_source`, `list_bookmarks`, `update_bookmark_tags`, `import_scope`, `export_scope`, `sync_from_global`, `sync_to_global`, `consolidate_knowledge` |
| **Lifespan wiring** | `bookmark_store`, `evaluator` (only used by bookmark pipeline), `bookmark_pipeline`, `consolidation_service`, `copilot_token.json` deletion |
| **AppContext fields** | `bookmark_pipeline`, `bookmark_store`, `consolidation_service` |
| **Helper functions** | `make_text_completion_fn()` (only used by consolidation) |
| **`__all__` entries** | 8 dead names: `bookmark_source`, `consolidate_knowledge`, `export_scope`, `import_scope`, `list_bookmarks`, `sync_from_global`, `sync_to_global`, `update_bookmark_tags` |

### 3.3 `__init__.py` Exports to Remove (6 symbols)

`Bookmark`, `BookmarkPipeline`, `BookmarkResult`, `BookmarkStore`, `ConsolidationInsight`, `ConsolidationService`

### 3.4 `pyproject.toml`

Remove `copilot` optional dependency group. Keep `llm` (for `llm_extractor.py` stub).

### 3.5 Test Impact Matrix

| Test File | Impact | Action |
|-----------|--------|--------|
| `tests/test_knowledge_ingest_source_identity_1556.py` | `AppContext(bookmark_pipeline=None, bookmark_store=None)` | Remove kwargs after AppContext cleanup |
| `tests/test_browser_fetcher_wiring.py` | Patches `BookmarkStore`, `BookmarkPipeline`, `ConsolidationService`, `make_evaluate_fn` in lifespan | Remove patches after lifespan cleanup |
| `tests/test_persistence_source_wiring.py` | Patches `make_evaluate_fn` (3 occurrences) | Remove patches |
| `tests/test_server.py:TestFromAC_TokenFileCleanup` | Tests `copilot_token.json` deletion | Delete entire test class — validates now-removed code |
| `tests/test_core_removal.py` | Tests `resolve_global_db_path` raises `NotImplementedError` | Delete relevant tests — module being deleted |
| `serve/mcp-knowledge/tests/test_server.py` | `_bypass_copilot_auth` fixture | Remove fixture — no copilot auth branch left |
| `serve/mcp-knowledge/tests/test_ingest_graph_tools.py` | `_bypass_copilot_auth` fixture | Remove fixture |
| `serve/mcp-knowledge/tests/test_ingest_graph_wiring.py` | `_bypass_copilot_auth` fixture | Remove fixture |

### 3.6 `make_evaluate_fn` Retention Analysis

`make_evaluate_fn()` feeds `SourceEvaluator(llm_fn=...)`. After retirement, `SourceEvaluator`
is only used by the bookmark pipeline — **it is also dead.** However, `SourceEvaluator` is
exported from `__init__.py` and referenced in the research doc as "keep." Let me verify:

- `SourceEvaluator` is created in the lifespan solely to feed `BookmarkPipeline`.
- No active MCP tool uses `SourceEvaluator` directly.
- But `SourceEvaluator` is exported and listed in the README as an active module.

**Risk:** Removing `SourceEvaluator` from the lifespan wiring is safe (it's only used by
bookmark pipeline), but **do not delete** `evaluator.py` or its export — it's classified
as "keep" in #1576. Only remove the lifespan wiring that creates the evaluator instance
for the bookmark pipeline. `make_evaluate_fn()` can also be removed since it was only
used to construct the evaluator for the bookmark pipeline.

## 4. Recommendation

**Confidence: 0.90** — Straightforward mechanical deletion. All retire targets confirmed
to have zero active callers in current codebase. Test cleanup is the only non-trivial part.

**Challenge: SKIPPED** — No alternatives to challenge; upstream #1576 already decided
the classification. This is pure execution validation.

**Implementation risk:** Low. Primary risk is test fixtures that reference retired symbols
breaking. The test impact matrix (§3.5) covers all affected files. No runtime callers
means no functional regression from the deletions themselves.

## 5. Follow-up Tasks

No new follow-up tasks needed — #1582 itself is the execution task, already scoped with
clear AC. Schema table removal is #1583. Stub labeling is #1584. All three were created
by #1576.
