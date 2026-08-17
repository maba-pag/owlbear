# Extract retrieval.py (GraphAugmentedRetriever)

> **Owning task:** #159 — Extract retrieval.py (GraphAugmentedRetriever)
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #159 calls for extracting `v1/src/owlbear/memory/knowledge/retrieval.py` (228 LOC) into `packages/knowledge/src/owlbear_knowledge/retrieval.py`. Key questions: (a) Are v2 interfaces compatible with the v1 retriever? (b) What import path changes are needed? (c) Are there any dependency or architectural issues?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| v1 retrieval.py (local, 228 LOC) | `v1/src/owlbear/memory/knowledge/retrieval.py` | `1.0` |
| v2 protocol.py (local, 78 LOC) | `packages/knowledge/src/owlbear_knowledge/protocol.py` | `1.0` |
| v2 graph_store.py (local) | `packages/knowledge/src/owlbear_knowledge/graph_store.py` | `1.0` |
| v2 embeddings.py (local) | `packages/knowledge/src/owlbear_knowledge/embeddings.py` | `1.0` |
| v2 models.py (local) | `packages/knowledge/src/owlbear_knowledge/models.py` | `1.0` |
| graph-augmented-retrieval.md (internal) | `docs/research/graph-augmented-retrieval.md` | `.95` |
| graph-augmented-retrieval-impl.md (internal) | `docs/research/graph-augmented-retrieval-impl.md` | `.95` |
| MS GraphRAG Local Search | `microsoft.github.io/graphrag/query/local_search` | `.85` |
| LightRAG (HKUDS, EMNLP 2025) | `github.com/HKUDS/LightRAG` | `.85` |

## 3. Analysis

### 3.1 v2 Interface Compatibility

Every type the v1 retriever depends on already exists in v2 with matching signatures:

| v1 import | v2 equivalent | Signature match? |
|-----------|---------------|-----------------|
| `owlbear.memory.knowledge.protocol.HybridEmbedding` | `owlbear_knowledge.protocol.HybridEmbedding` | Exact |
| `owlbear.memory.knowledge.protocol.VectorStoreProtocol` | `owlbear_knowledge.protocol.VectorStoreProtocol` | Exact — `search_similar(embedding, top_k, embedding_type, scopes)` |
| `owlbear.memory.knowledge.embeddings.EmbeddingProvider` | `owlbear_knowledge.embeddings.EmbeddingProvider` | Exact — `embed(texts) -> list[list[float]]` |
| `owlbear.memory.knowledge.graph.GraphStore` | `owlbear_knowledge.graph_store.GraphStore` | Exact — `get_neighbors(entity_id, max_depth, max_nodes, scopes)` returns `list[tuple[Entity, Edge]]` |
| `owlbear.memory.knowledge.models.Entity` | `owlbear_knowledge.models.Entity` | Exact — has `chunk_id`, `importance`, `name`, `description` |

**Finding: The extraction is a direct port with zero logic changes.** Only 5 import lines change.

### 3.2 Import Path Migration

```python
# v1 (5 lines to change)
from owlbear.memory.knowledge.protocol import HybridEmbedding
from owlbear.memory.knowledge.embeddings import EmbeddingProvider
from owlbear.memory.knowledge.graph import GraphStore  # → graph_store
from owlbear.memory.knowledge.models import Entity
from owlbear.memory.knowledge.protocol import VectorStoreProtocol

# v2 (after migration)
from owlbear_knowledge.protocol import HybridEmbedding
from owlbear_knowledge.embeddings import EmbeddingProvider
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Entity
from owlbear_knowledge.protocol import VectorStoreProtocol
```

Note: v1 imports from `graph` (module alias); v2 module is `graph_store`.

### 3.3 Architectural Validation

The dual-path search + BFS expansion pattern in v1 is validated by two independent sources:

- **MS GraphRAG Local Search**: entity-based reasoning with neighbor fan-out and context-window budget (docs/research/graph-augmented-retrieval.md §3.1)
- **LightRAG "mix" mode**: KG + vector search with token budgets (`max_entity_tokens`, `max_relation_tokens`) — validates the budget-cap approach (docs/research/knowledge-package-integration-hybrid-search.md §3.3)

The v1 implementation follows KISS: 228 LOC, single class, three private helpers. No new abstractions needed.

### 3.4 Dependency Check

- `depends_on: [32]` — #32 (vector store + embedding pipeline) is at `todo`. The retriever depends on `VectorStoreProtocol` and `EmbeddingProvider` which already exist in v2 code. Tests can use mocks. **No blocker for extraction; dependency is for runtime wiring, not code existence.**
- No new pip dependencies — only `pydantic` (already in `pyproject.toml`).
- Zero PydanticAI or daemon imports in v1 retrieval.py — confirmed by grep.

### 3.5 Testing Strategy

Mock all three constructor dependencies:

| Mock | Key behaviors |
|------|--------------|
| `VectorStoreProtocol` | `search_similar()` returns configurable `list[tuple[str, float]]` |
| `GraphStore` | `list_entities()` returns entities with known `chunk_id`; `get_neighbors()` returns `list[tuple[Entity, Edge]]` |
| `EmbeddingProvider` | `embed()` returns fixed vectors; optionally `embed_hybrid()` |

Test cases: (1) retrieve with expansion enabled, (2) retrieve with expansion disabled, (3) empty vector results → early return, (4) no seeds resolved → vector-only fallback, (5) budget cap hit mid-expansion → truncation, (6) `weight_by_importance=True` → sorted neighbors, (7) `_word_count` helper accuracy.

### 3.6 Package Integration

After extraction, `__init__.py` should export `GraphAugmentedRetriever` and `RetrievalResult`. The v2 `query_service.py` currently has a placeholder `retriever: object | None = None` parameter — wiring the retriever is a separate task (#34 scope per prior research).

## 4. Recommendation (.95 confidence)

**Direct port with import path migration.** Zero logic changes. The AC is precise and achievable:

- Copy v1 `retrieval.py` → v2 path
- Replace 5 import lines (`owlbear.memory.knowledge.*` → `owlbear_knowledge.*`)
- Merge the two `protocol` imports into one line
- Add exports to `__init__.py`
- Create unit tests with mock dependencies

**Risk:** Low. All interfaces match exactly. The only non-obvious detail is the `graph` → `graph_store` module rename, which the builder must catch.

## 5. Follow-up Tasks

No new follow-up tasks needed — #159 already has precise AC that covers the full extraction scope. The preceding test task should be created by the architect if one doesn't already exist (per TDD convention). Retriever wiring into `query_service.py` is #34 scope.
