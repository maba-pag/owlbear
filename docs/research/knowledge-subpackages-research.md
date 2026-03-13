# Knowledge Sub-Packages: Split or Keep Flat?

> **Owning task:** #566 — Consider sub-packages for knowledge/ directory (22 files)
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

The `src/owlbear/memory/knowledge/` package has 22 `.py` files (21 modules + `__init__.py`, ~4,300 LOC). The software design audit (MOD-04) flagged this as a potential modularity issue and suggested splitting into `storage/`, `pipeline/`, `retrieval/` sub-packages. Should we split?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | LlamaIndex core layout | <https://github.com/run-llama/llama_index/tree/main/llama-index-core/llama_index/core> | .85 |
| 2 | LangChain core layout | <https://github.com/langchain-ai/langchain/tree/master/libs/core/langchain_core> | .80 |
| 3 | PEP 20 / Python Packaging Guide | <https://docs.python-guide.org/writing/structure/> | .75 |
| 4 | Ionel Cristian Maries, "Packaging a Python library" | <https://blog.ionelmc.ro/2014/05/25/python-packaging/> | .70 |

## 3. Analysis

### 3a. File Categorization (22 files)

| Group | Files | Count | LOC |
|-------|-------|-------|-----|
| **Foundation** (models, types) | `models.py`, `protocol.py`, `schema.py` | 3 | 426 |
| **Storage** (persistence) | `graph.py`, `qdrant.py`, `source_store.py`, `bookmark.py` | 4 | 1,137 |
| **Pipeline** (ingestion) | `ingest.py`, `chunker.py`, `extractor.py`, `embeddings.py`, `intake.py`, `graph_builder.py`, `inter_doc_graph_builder.py` | 7 | 1,496 |
| **Retrieval** (querying) | `retrieval.py`, `query_service.py` | 2 | 335 |
| **Evaluation** (bookmarks) | `bookmark_pipeline.py`, `bookmark_toolset.py`, `evaluator.py` | 3 | 390 |
| **Orchestration** | `refresh.py` | 1 | 177 |

### 3b. Coupling Metrics

| Metric | Value |
|--------|-------|
| Internal cross-imports | 15 modules import from other knowledge modules |
| External production imports | 8 (from `core/agent.py`, `tools/knowledge.py`, `tools/knowledge_source.py`) |
| Test file imports | 60+ across ~20 test files |
| Circular imports | **None** (verified clean) |

### 3c. Comparison with Other OwlBear Packages

| Package | .py files (flat) | Sub-packages | Layout |
|---------|------------------|--------------|--------|
| `core/` | 19 | 0 | Flat |
| `tools/` | 17 | 1 (`browser/`) | Mostly flat |
| `memory/knowledge/` | 21 | 0 | Flat |
| `channels/` | 6 | 0 | Flat |

### 3d. Prior Art Comparison

| Criterion | Split (.35) | Keep flat (.80) |
|-----------|-------------|-----------------|
| **KISS** | Adds nesting, 3+ `__init__.py` files, deeper import paths | One namespace, short imports |
| **YAGNI** | No current pain (no circular imports, no navigation bugs) | Current layout works |
| **Churn cost** | 60+ test imports, 8 production imports, merge conflicts | Zero |
| **Discoverability** | Slightly better grouping in file tree | `__init__.py` already groups 35 public symbols |
| **Prior art support** | LlamaIndex/LangChain split (but at 40+ dirs, 10x scale) | PEP 20: "Flat is better than nested" |
| **Scalability** | Better if package grows past 30 files | Adequate at 22 files, may revisit later |

## 4. Recommendation (.80 confidence): Keep Flat

**Keep the flat layout.** The refactoring cost is high (60+ import updates, potential merge conflicts, zero functional improvement) and the benefit is marginal navigability improvement. The existing `__init__.py` already provides a well-organized public API with 35 symbols grouped logically.

**Key reasons:**

- **No actual pain.** No circular imports, no navigation complaints from developers, no bugs caused by the flat layout.
- **PEP 20 alignment.** "Flat is better than nested" — splitting adds complexity without solving a real problem.
- **Proportional scale.** LlamaIndex/LangChain split because they have 40+ directories. At 22 files, we're below that threshold. Our own `core/` has 19 files flat without issue.
- **YAGNI.** The task description itself says "Low priority — current layout works."

**Revisit trigger:** Split if the package exceeds 30 files OR circular import issues emerge OR a new developer reports confusion navigating the package.

## 5. Follow-up Tasks

No implementation tasks needed — the decision is to keep the current layout. The only action is to close #566 with the decision documented.

If the package grows past 30 files in the future, the recommended split would be:

- `knowledge/storage/` — `graph.py`, `qdrant.py`, `source_store.py`, `bookmark.py`
- `knowledge/pipeline/` — `ingest.py`, `chunker.py`, `extractor.py`, `embeddings.py`, `intake.py`, `graph_builder.py`, `inter_doc_graph_builder.py`
- `knowledge/retrieval/` — `retrieval.py`, `query_service.py`
- `knowledge/` (root) — `models.py`, `protocol.py`, `schema.py`, `evaluator.py`, `bookmark_pipeline.py`, `bookmark_toolset.py`, `refresh.py`
