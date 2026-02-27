# Knowledge Graph + Vector DB Technology for OwlBear

> **Owning task:** #50 — Research knowledge graph + vector DB technology
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear needs structured long-term memory — a knowledge graph with vector embeddings — to store entities (files, functions, decisions, patterns), relationships between them, and enable semantic similarity search. This sits **alongside** existing memory: `ContextManager` (static instructions) and `SessionStore` (JSONL conversation history). The knowledge graph adds persistent, queryable, structured memory that survives across sessions.

**Key constraints:** laptop-resident (no servers), Python 3.12+, minimal dependencies (KISS), single-file DB preferred, must work offline.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| tool.graphicator | Local: `C:\Users\...\tool.graphicator` | .95 | User's prior art — SQLite + sqlite-vec KG with Pydantic models, CRUD, vector search, rowid_map bridge |
| sqlite-vec | github.com/asg017/sqlite-vec | .90 | Pure C SQLite extension for vector search — 7k stars, pre-built Python wheels, runs anywhere |
| FastEmbed (Qdrant) | github.com/qdrant/fastembed | .85 | Local ONNX-based embedding generation — no GPU needed, 384-dim default model, Apache-2.0 |
| nano-graphrag | github.com/gusye1234/nano-graphrag | .80 | ~1100 LOC GraphRAG — networkx graph + nano-vectordb, pluggable backends, async |
| LightRAG (HKUDS) | github.com/HKUDS/LightRAG | .70 | Full-featured GraphRAG — networkx default graph, nano-vectordb default vector, 28.7k stars |
| ChromaDB | github.com/chroma-core/chroma | .50 | Vector DB with embedded mode — 26.3k stars, but Rust/Go backend, heavy dependency tree |
| LanceDB | github.com/lancedb/lancedb | .45 | Embedded vector DB on Lance format — 9.1k stars, Rust-based, columnar storage, heavier |
| microsoft/graphrag | github.com/microsoft/graphrag | .40 | Reference GraphRAG implementation — heavyweight, server-oriented, "expensive operation" per README |

## 3. Analysis

### 3.1 Vector Storage — Comparison

| Criterion | sqlite-vec (.90) | ChromaDB (.45) | LanceDB (.40) |
|-----------|-------------------|----------------|----------------|
| Dependency count | 1 (sqlite ext) | ~30+ packages | ~15 packages (Rust FFI) |
| Disk footprint | ~2 MB wheel | ~50 MB+ (Rust backend) | ~30 MB+ |
| Server required | No (in-process) | No (embedded) but designed for client-server | No (embedded) |
| Python 3.12 | Yes (wheels available) | Yes | Yes |
| Storage format | SQLite file | Parquet + custom | Lance columnar |
| Query API | Raw SQL (`MATCH`, `k=`) | Python ORM-like | Python + SQL |
| KISS score | **High** — it's just SQLite | Low — large abstraction | Medium |
| Prior art in project | **Yes** (tool.graphicator) | No | No |
| Metadata filtering | Yes (v0.1.6+ auxiliary/partition columns) | Yes (native) | Yes (native) |
| Index type | Brute-force (exact KNN) | HNSW | IVF-PQ, brute-force |

**Verdict:** sqlite-vec wins decisively for a laptop-resident system. It's a single SQLite extension with pre-built wheels, zero additional services, and the user already has working code (tool.graphicator). ChromaDB and LanceDB add significant dependency weight for features OwlBear doesn't need.

### 3.2 Graph Storage — Comparison

| Criterion | SQLite tables (.85) | networkx (.75) | Neo4j (.20) |
|-----------|---------------------|----------------|-------------|
| Persistence | Native (file) | Requires serialization (JSON/pickle) | Server process |
| Query | SQL JOINs, CTEs | Python API, path algorithms | Cypher |
| Dependencies | 0 (stdlib) | 1 package | Server + driver |
| Laptop-resident | **Yes** | Yes (in-memory only) | No (server) |
| KISS score | **High** | Medium | Low |
| Graph algorithms | Manual (BFS/DFS in Python) | Built-in (shortest_path, centrality, etc.) | Built-in |
| Prior art in project | **Yes** (tool.graphicator schema) | No | No |
| Scales to | ~1M entities comfortably | ~100K entities (RAM-bound) | Millions+ |

**Verdict:** SQLite-based graph storage (entities + edges tables with SQL joins) is the right choice. It shares the same DB file as vector storage (single `.db` file), has zero dependencies, and tool.graphicator already implements it. networkx is useful if we need complex graph algorithms later, but can be loaded on-demand from the SQLite data — not as the primary store.

### 3.3 Embedding Model — Comparison

| Criterion | FastEmbed/ONNX local (.85) | OpenAI API (.60) | sentence-transformers (.65) |
|-----------|---------------------------|-------------------|---------------------------|
| Offline | **Yes** | No | Yes |
| Dependencies | ONNX Runtime (~15 MB) | httpx (already have) | PyTorch (~2 GB) |
| Speed (CPU) | Fast (ONNX optimized) | Network-bound | Moderate |
| Default dim | 384 (bge-small-en-v1.5) | 1536 (text-embedding-3-small) | 384–768 |
| Model size | ~30 MB (small models) | N/A (API) | ~90 MB – 500 MB |
| KISS score | **High** | High (but network) | Low (huge deps) |

**Verdict:** FastEmbed is the best fit. It runs locally with ONNX Runtime (no PyTorch), supports Python 3.12+, the default `BAAI/bge-small-en-v1.5` model is 384-dim at ~33 MB, and tool.graphicator already uses it. For an optional API fallback (when GitHub Copilot adds embedding endpoints), the adapter pattern makes this pluggable.

### 3.4 tool.graphicator Reuse Assessment

| Component | File | Reusable? | Adaptation needed |
|-----------|------|-----------|-------------------|
| Schema DDL | `db/schema.py` | **Yes** (.90) | Rename tables/types for OwlBear domain, drop graphicator-specific `DocType` enums |
| Graph CRUD | `db/graph.py` | **Yes** (.85) | Adapt row converters to OwlBear models, add async wrappers |
| Vector ops | `db/vectors.py` | **Yes** (.90) | Minimal changes — rowid_map bridge pattern is solid |
| Pydantic models | `models.py` | **Partial** (.70) | Need OwlBear-specific entity types (file, function, decision, pattern) |
| Embeddings agent | `agents/embeddings.py` | **No** (.30) | Uses OpenAI API directly; replace with FastEmbed local |
| Queries | `db/queries.py` | **Partial** (.50) | BFS traversal reusable; domain-specific queries not applicable |
| Freeze mechanism | schema triggers | **Yes** (.85) | Good pattern for immutable historical snapshots |

## 4. Recommendation (.85 confidence)

**SQLite + sqlite-vec + FastEmbed**, adapted from tool.graphicator.

### Architecture

```
owlbear/memory/
├── context.py       # (existing) Static workspace instructions
├── session.py       # (existing) JSONL conversation persistence
├── __init__.py      # (existing) Public API
├── knowledge/       # (new) Knowledge graph subpackage
│   ├── __init__.py
│   ├── schema.py    # DDL + init_db (adapted from tool.graphicator)
│   ├── models.py    # Pydantic models: Entity, Edge, Document
│   ├── graph.py     # CRUD operations (adapted from tool.graphicator)
│   ├── vectors.py   # Embedding storage + similarity search
│   └── embeddings.py # FastEmbed adapter (local ONNX models)
```

### Key design decisions

1. **Single SQLite file** — `~/.owlbear/knowledge.db` — graph + vectors in one file. Configured via `OwlBearSettings.knowledge_db_path`.
2. **FastEmbed for local embeddings** — 384-dim `BAAI/bge-small-en-v1.5` by default. Configurable model name in settings.
3. **Adapter pattern for embeddings** — Protocol-based `EmbeddingProvider` so we can swap FastEmbed for API-based models later.
4. **Entity types for dev context** — `file`, `function`, `class`, `decision`, `pattern`, `concept` (not graphicator's `control`/`clause`).
5. **Relationship types** — `defines`, `imports`, `depends_on`, `related_to`, `implements`, `documents`.
6. **Freeze mechanism preserved** — Immutable snapshots prevent accidental mutation of historical knowledge.
7. **Async wrapper** — Wrap synchronous sqlite3 calls with `asyncio.to_thread` for non-blocking agent integration.

### Risks and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| sqlite-vec brute-force search slow at scale | Low (laptop = ~10K entities) | Acceptable for <50K vectors; partition by workspace if needed |
| FastEmbed model download on first use | Low | Pre-download in `bearclaw setup`; cache in `~/.owlbear/models/` |
| Schema migration complexity | Medium | Version table (already in tool.graphicator); simple `ALTER TABLE` migrations |
| Embedding dimension mismatch if model changes | Medium | Store model name + dim in metadata table; validate on startup |

## 5. Follow-up Tasks

1. **Add sqlite-vec and fastembed to pyproject.toml** — New optional dependency group `[knowledge]`.
2. **Create owlbear.memory.knowledge.schema** — DDL adapted from tool.graphicator with OwlBear entity types.
3. **Create owlbear.memory.knowledge.models** — Pydantic models for Entity, Edge, Document records.
4. **Create owlbear.memory.knowledge.graph** — CRUD operations adapted from tool.graphicator.
5. **Create owlbear.memory.knowledge.vectors** — Vector storage + similarity search (rowid_map bridge).
6. **Create owlbear.memory.knowledge.embeddings** — FastEmbed adapter with EmbeddingProvider protocol.
7. **Add knowledge_db_path to OwlBearSettings** — Config for DB file location.
8. **Write tests for knowledge subpackage** — Unit tests for schema, models, graph, vectors, embeddings.

