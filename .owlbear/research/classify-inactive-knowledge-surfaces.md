# Classify Inactive Knowledge Surfaces

> **Owning task:** #1576 — Classify inactive knowledge surfaces
> **Date:** 2026-05-15 **Status:** Complete

## 1. Context and Question

The knowledge module has 8 active MCP tools but retains ~11 plain functions in `server.py` and ~6 library modules that are not reachable via any active MCP tool. Which should be retired (deleted), which should be documented as intentional stubs for future work, and which should be kept as-is?

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| 1 | server.py (current) | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | 1.0 |
| 2 | knowledge `__init__.py` | `serve/knowledge/src/owlbear_knowledge/__init__.py` | 0.9 |
| 3 | Research: MCP tool surface validation (#1334) | `.owlbear/research/mcp-knowledge-tool-surface-validation.md` | 0.9 |
| 4 | Research: dead-code tools.py (#223) | `.owlbear/research/dead-code-mcp-knowledge-tools.md` | 0.7 |
| 5 | scope_transfer.py | `serve/knowledge/src/owlbear_knowledge/scope_transfer.py` | 0.9 |
| 6 | consolidation.py | `serve/knowledge/src/owlbear_knowledge/consolidation.py` | 0.9 |
| 7 | copilot_auth.py | `serve/knowledge/src/owlbear_knowledge/copilot_auth.py` | 0.8 |
| 8 | h-knowledge-ops handbook | `share/skills/h-knowledge-ops/SKILL.md` | 0.9 |
| 9 | pyproject.toml (knowledge) | `serve/knowledge/pyproject.toml` | 0.7 |

## 3. Analysis — Classification Matrix

### 3.1 Inactive Functions in server.py

| Function | Active Callers | Classification | Rationale |
|----------|---------------|----------------|-----------|
| `list_entities` | None | **Document-as-stub** | Useful future graph-browsing tool; needs thread-safety review before exposure |
| `knowledge_stats` | Internal only | **Keep** | Helper for active `get_stats` tool |
| `knowledge_stats_resource` | Internal only | **Keep** | Helper for `knowledge://stats` resource |
| `bookmark_source` | None | **Retire** | BookmarkPipeline has no dedup contract; wired in lifespan but never exposed |
| `list_bookmarks` | None | **Retire** | BookmarkStore inactive; no tool decorator |
| `update_bookmark_tags` | None | **Retire** | Same |
| `import_scope` | None | **Retire** | Schema is lossy (missing source_id, enrichment state); no portability contract |
| `export_scope` | None | **Retire** | Same |
| `sync_from_global` | None | **Retire** | Always raises `NotImplementedError` since #1296 |
| `sync_to_global` | None | **Retire** | Same |
| `consolidate_knowledge` | None | **Retire** | LLM backend is empty-string stub; would mark chunks consolidated with no insight |

### 3.2 Library Modules in serve/knowledge/

| Module | Imported By Active Code | Classification | Rationale |
|--------|------------------------|----------------|-----------|
| `bookmark_pipeline.py` | server.py lifespan (wired, never called) | **Retire** | No active tool or consumer |
| `bookmark_store.py` | server.py lifespan (wired, never called) | **Retire** | Same |
| `consolidation.py` | server.py lifespan (wired with no-op LLM) | **Retire** | Active Phase 2 uses `get_consolidation_candidates` + `store_enrichment` — a different mechanism |
| `copilot_auth.py` | Not imported by server src; lifespan only deletes its token file | **Retire** | OAuth flow for removed LLM backend; token is unconditionally deleted on startup |
| `llm_extractor.py` | Not imported anywhere | **Document-as-stub** | Prompt constants + incomplete class for future #875; keep as intentional stub |
| `inter_doc_graph_builder.py` | Set to `None` in lifespan | **Document-as-stub** | Real impl exists; requires StructuredExtractor; future capability |
| `scope_transfer.py` | server.py imports 4 symbols | **Retire** | Lossy schema, global path removed; no portability contract |
| `benchmark.py` | Standalone CLI | **Keep** | Quality benchmark with `python -m owlbear_knowledge.benchmark`; still useful |
| `content_safety.py` | `ingest.py` imports `should_wrap`, `wrap_untrusted_content` | **Keep** | Active security utility |

### 3.3 Schema Tables

| Table | Active Write Path | Classification | Note |
|-------|-------------------|----------------|------|
| `bookmarks` | None | **Retire** | Drop from schema; no data in production |
| `consolidations` | None (only via no-op `consolidate_knowledge`) | **Retire** | Drop from schema; Phase 2 uses `reviewed_pairs` + `edges` |

### 3.4 Package Exports & Dependencies

| Item | Classification | Action |
|------|----------------|--------|
| `__init__.py` exports: `BookmarkPipeline`, `BookmarkResult`, `BookmarkStore`, `Bookmark`, `ConsolidationInsight`, `ConsolidationService` | **Retire** | Remove with module deletion |
| `pyproject.toml` optional dep `copilot = ["httpx", "truststore"]` | **Retire** | Remove with `copilot_auth.py` |
| `pyproject.toml` optional dep `llm = ["openai"]` | **Keep** | Still needed by `llm_extractor.py` stub |
| `server.py __all__` entries for retired functions | **Retire** | Remove dead names |

### 3.5 Documentation

The `h-knowledge-ops` handbook is **already correct** and documents only 8 active tools.
The package README at `serve/knowledge/README.md` required a correction and now no
longer presents bookmark, scope-transfer, or consolidation surfaces as operational.
No skills or instructions reference inactive tools as operational.

## 4. Recommendation

**Confidence: 0.85** — Straightforward cleanup. Risk is low because all retire-targets have zero active callers. The two stub-classified modules (`llm_extractor`, `inter_doc_graph_builder`) are well-scoped future work and should get a brief docstring header marking them as deferred.

**Challenge: SKIPPED** — No alternative recommendations to challenge; this is a classification inventory, not an architectural choice.

**Implementation approach:**
1. **Phase A** — Retire dead functions from `server.py` (bookmark, scope, consolidate) + remove corresponding imports, `__all__` entries, and lifespan wiring.
2. **Phase B** — Delete retired library modules (`bookmark_pipeline.py`, `bookmark_store.py`, `consolidation.py`, `copilot_auth.py`, `scope_transfer.py`) + clean `__init__.py` exports + remove `copilot` optional dep.
3. **Phase C** — Drop `bookmarks` and `consolidations` tables from schema DDL + add migration step.
4. **Phase D** — Add `# DEFERRED` header comments to `llm_extractor.py`, `inter_doc_graph_builder.py`, and `list_entities` function.

Phases A+B can be one task. Phase C is separate (schema migration). Phase D is trivial.

## 5. Follow-up Tasks

| # | Title | Status | Scope |
|---|-------|--------|-------|
| 1 | Retire bookmark/scope/consolidation dead code from knowledge module | research | Phases A+B: delete functions, modules, imports, exports, optional dep |
| 2 | Drop bookmarks and consolidations tables from knowledge schema | research | Phase C: schema v12 migration |
| 3 | Label deferred knowledge stubs (llm_extractor, inter_doc_graph_builder, list_entities) | research | Phase D: docstring headers only |
