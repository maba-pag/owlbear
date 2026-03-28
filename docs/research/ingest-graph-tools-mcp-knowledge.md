# Ingest and Graph Tools for mcp-knowledge Server

> **Owning task:** #55 — Add ingest and graph tools to mcp-knowledge server
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #55 extends the mcp-knowledge server (scaffolded by #40) with three new tools: `ingest_document`, `list_entities`, and `get_stats`. This research validates tool design, parameter shapes, pagination strategy, and testing approach against prior art.

**Dependencies:** #40 (scaffold), search_knowledge implementation. The `packages/` directory does not yet exist — these tools will be added once the scaffold lands.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Qdrant MCP Server (v0.8.1) | <https://github.com/qdrant/mcp-server-qdrant> | .90 |
| 2 | MCP Official Memory Server | <https://github.com/modelcontextprotocol/servers/tree/main/src/memory> | .90 |
| 3 | FastMCP Tools Documentation | <https://gofastmcp.com/servers/tools> | .95 |
| 4 | OwlBear v1 KnowledgeToolset | `v1/src/owlbear/tools/knowledge.py` | .95 |
| 5 | OwlBear v1 GraphStore | `v1/src/owlbear/memory/knowledge/graph.py` | .95 |
| 6 | OwlBear v1 IngestPipeline | `v1/src/owlbear/memory/knowledge/ingest.py` | .95 |
| 7 | Scaffold research (#40) | `docs/research/scaffold-mcp-knowledge.md` | .90 |

## 3. Analysis

### 3.1 Prior Art Tool Surfaces

| Aspect | Qdrant MCP (Src 1) | MCP Memory (Src 2) | v1 KnowledgeToolset (Src 4) | AC #55 |
|--------|--------------------|--------------------|----------------------------|--------|
| Ingest | `qdrant-store(information, metadata)` | `create_entities(entities[])` | `ingest_document(source, doc_type)` | `ingest_document(text, metadata)` |
| List/Browse | — | `read_graph()`, `open_nodes(names[])` | `list_knowledge_sources()` | `list_entities(type, offset, limit)` |
| Stats | — | — | — | `get_stats()` |
| Total tools | 2 | 8 | 3 | 3 (additive) |

**Insight:** Qdrant uses `information` (string) + `metadata` (dict) — same shape as the AC. MCP Memory exposes full CRUD (8 tools) but has no stats. The v1 KnowledgeToolset has `ingest_document` with a `doc_type` discriminator — the AC simplifies this to text-only, which is KISS-aligned since the MCP server processes text content arriving from agents.

### 3.2 Tool Design for LLM Consumption

Best practices from FastMCP docs (Src 3) and MCP Memory (Src 2):

| Practice | Source | Application |
|----------|--------|-------------|
| Use `Annotated[type, "description"]` for params | Src 3 | All 3 tools |
| Verb-first tool descriptions | Src 1, Src 2 | "Ingest a text...", "List entities...", "Get summary..." |
| `readOnlyHint` annotation | Src 3 | `list_entities`, `get_stats` = True; `ingest_document` = False |
| Return structured text, not raw dicts | Src 1, Src 4 | Format results as numbered/bulleted text |
| Keep param count low (≤5) | Src 1 | All tools have 2-4 params |

### 3.3 Pagination Strategy

| Option | Complexity | MCP Precedent | KISS Score |
|--------|-----------|---------------|------------|
| Offset + limit | Low | None (custom) | High |
| Cursor-based | Medium | None | Medium |
| No pagination (return all) | Lowest | MCP Memory `read_graph()` | Highest for small graphs |

**Recommendation (.85):** Offset-based pagination with `offset=0, limit=50`. SQLite OFFSET/LIMIT maps directly. The MCP Memory server returns everything in `read_graph()`, but OwlBear's graph can grow large. A `limit` param with reasonable default prevents context overflow. No cursor complexity needed for local SQLite. Add `total_count` in the response header for the LLM to know if more pages exist.

### 3.4 `get_stats` Implementation

`GraphStore` has `list_entities()`, `list_edges()`, `list_documents()` but no count-only methods. Two options:

| Option | Approach | Performance |
|--------|----------|-------------|
| A. Count via len(list_*()) | Reuse existing methods | O(n) — loads all rows |
| B. SQL COUNT queries | New `get_counts()` method on GraphStore | O(1) — DB-level aggregation |

**Recommendation (.90):** Option B. Three COUNT queries are trivial to add and avoid loading entire tables into memory. The builder should add a `get_counts()` method to `GraphStore` returning `(doc_count, entity_count, edge_count)`.

### 3.5 Lifespan Context Extension

The scaffold research (#40, Src 7) defines `AppContext` with `query_service` and `graph`. For the new tools, `IngestPipeline` must be added to the lifespan context:

```python
@dataclass(frozen=True)
class AppContext:
    query_service: KnowledgeQueryService
    graph: GraphStore
    ingest_pipeline: IngestPipeline  # NEW — needed by ingest_document tool
```

The `IngestPipeline` requires `DocumentStore`, `EntityExtractor`, `TextChunker`, and `workspace_root` — all wired during lifespan init. This is a natural extension of the existing pattern.

### 3.6 Testing Strategy

| Layer | What | Mock/Fixture | Source |
|-------|------|--------------|--------|
| Unit | `ingest_document` return format | Mock `IngestPipeline.ingest_text` returning `IngestResult` | Src 4, Src 6 |
| Unit | `list_entities` pagination + filtering | Mock `GraphStore.list_entities` returning `[Entity, ...]` | Src 5 |
| Unit | `get_stats` counts | Mock `GraphStore.get_counts` returning tuple | New method |
| Unit | Error handling (pipeline failure) | Mock raising exception | Src 3 |

FastMCP tools can be tested by calling the function directly with a mock `Context` object (Src 1 pattern). No full MCP protocol round-trip needed for unit tests.

## 4. Recommendation (.85 confidence)

Proceed with all 3 tools as scoped in the AC. Key design decisions:

1. **`ingest_document`**: Accept `text` (str) + `metadata` (dict | None). Delegate to `IngestPipeline.ingest_text()`. Return formatted summary string.
2. **`list_entities`**: Offset-based pagination (`offset=0, limit=50`). Filter by `entity_type` (optional). Return total count in response.
3. **`get_stats`**: Add `get_counts()` to `GraphStore` with SQL COUNT queries. Return formatted string with 3 counts.
4. **Annotations**: `readOnlyHint=True` for read tools, `False` for ingest.
5. **Lifespan**: Add `IngestPipeline` to scaffold's `AppContext`.

**Risk:** IngestPipeline requires `EntityExtractor` (LLM-based) — the lifespan must configure a model. For tests, mock the entire pipeline. For production, env var `OWLBEAR_MODEL` or default.

## 5. Follow-up Tasks

Task #55 itself is the implementation task (already at ideation). The AC is well-scoped. No additional decomposition needed — the 3 tools + tests fit in a single builder task. The architect should refine AC with:

- Offset-based pagination for `list_entities` (offset/limit params)
- `get_counts()` method addition to `GraphStore`
- `IngestPipeline` added to `AppContext` lifespan
- `readOnlyHint` annotations on read-only tools
