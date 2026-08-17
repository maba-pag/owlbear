# Scaffold mcp-knowledge MCP Server Package

> **Owning task:** #40 — Scaffold mcp-knowledge MCP server package
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #40 asks for scaffolding `packages/mcp-knowledge/` with a FastMCP server exposing the OwlBear knowledge engine via MCP. This research validates feasibility for each AC item (package structure, lifespan, tool surface, VS Code registration, testing) and provides an implementation blueprint.

Prior research: `docs/research/mcp-python-sdk.md` (#2) established the FastMCP v1 API, stdio transport recommendation, and lifespan pattern. `docs/research/monorepo-tooling.md` (#6) established the uv workspace cross-package import pattern.

## 2. Sources

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | MCP Python SDK README (v1 stable) | <https://github.com/modelcontextprotocol/python-sdk> | .95 |
| 2 | Qdrant MCP Server | <https://github.com/qdrant/mcp-server-qdrant> | .90 |
| 3 | MCP Resources Spec | <https://modelcontextprotocol.io/docs/concepts/resources> | .80 |
| 4 | MCP Official Memory Server | <https://github.com/modelcontextprotocol/servers/tree/main/src/memory> | .85 |
| 5 | OwlBear v1 knowledge engine | `v1/src/owlbear/memory/knowledge/` | .95 |
| 6 | OwlBear monorepo-tooling research | `docs/research/monorepo-tooling.md` | .90 |
| 7 | OwlBear MCP SDK research | `docs/research/mcp-python-sdk.md` | .95 |

## 3. Prior Art Comparison

| Aspect | Qdrant MCP (Src 2) | MCP Memory (Src 4) | OwlBear mcp-knowledge |
|--------|--------------------|--------------------|----------------------|
| Store | Qdrant (vector only) | In-memory graph | SQLite graph + Qdrant vector |
| Tools | `store`, `find` (2) | `create_entities`, `search_nodes`, etc. (8) | `search_knowledge` (scaffold), expand later |
| Transport | stdio (default) | stdio | stdio |
| Lifespan | Qdrant client + embeddings | None (in-memory) | SQLite init_db + Qdrant + embeddings |
| Config | Env vars | Env vars | Env vars (OWLBEAR_ prefix) |
| Embedding | FastEmbed (external) | None | BGE-M3 (internal) |
| Package size | ~400 LOC | ~300 LOC | ~150 LOC (scaffold) |

**Insight:** Both reference servers use minimal tool surfaces (2–8 tools). OwlBear should start with 1 placeholder tool per AC, then expand. The Qdrant server's lifespan is the closest pattern to what we need (external vector DB connection).

## 4. Feasibility by AC Item

### 4.1 Package Structure

Per monorepo-tooling.md (Src 6), the package layout is:

```
packages/mcp-knowledge/
├── pyproject.toml          # uv_build backend, depends on owlbear-knowledge
├── src/mcp_knowledge/
│   ├── __init__.py
│   ├── __main__.py          # python -m mcp_knowledge entry point
│   └── server.py            # FastMCP instance + tools
└── tests/
    └── test_server.py
```

The `pyproject.toml` needs `[tool.uv.sources] owlbear-knowledge = { workspace = true }` for cross-package imports. **Feasibility: confirmed** (Src 6, pattern validated in pydantic-ai monorepo).

### 4.2 FastMCP with stdio

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("owlbear-knowledge", lifespan=app_lifespan)
# ... tool registrations ...
mcp.run()  # stdio by default
```

**Feasibility: confirmed** (Src 1, Src 7). The `mcp.run()` call handles stdio transport automatically. VS Code manages the process lifecycle.

### 4.3 Lifespan for SQLite/Qdrant

The v1 knowledge engine has these key components (Src 5):

| Component | Module | Sync/Async | Lifespan role |
|-----------|--------|------------|---------------|
| `init_db` | `schema.py` | Sync | Initialize SQLite schema |
| `GraphStore` | `graph.py` | Sync | Entity/edge CRUD (sqlite3) |
| `QdrantVectorStore` | `qdrant.py` | Async | Vector search (qdrant-client) |
| `BgeM3EmbeddingProvider` | `embeddings.py` | Sync (lazy) | Embedding generation |
| `KnowledgeQueryService` | `query_service.py` | Async | Orchestrates search |

The lifespan pattern composes these:

```python
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    db_path = Path(os.environ.get("OWLBEAR_KB_PATH", "knowledge.db"))
    conn = init_db(db_path)
    graph = GraphStore(conn)
    embeddings = BgeM3EmbeddingProvider()
    vector_store = QdrantVectorStore(...)
    query_service = KnowledgeQueryService(graph, vector_store, embeddings)
    try:
        yield AppContext(query_service=query_service, graph=graph)
    finally:
        conn.close()
```

**Sync/async concern:** `GraphStore` uses synchronous sqlite3. This is safe in an async context for local file I/O — SQLite operations on a local file are effectively non-blocking (< 1 ms). The Qdrant MCP server (Src 2) uses a similar pattern with sync initialization in async lifespan. **Feasibility: confirmed.**

### 4.4 Placeholder Tool

For the scaffold, a single tool with placeholder logic:

```python
@mcp.tool()
async def search_knowledge(query: str, limit: int = 5, ctx: Context) -> str:
    """Search the OwlBear knowledge base for relevant information."""
    app = ctx.request_context.lifespan_context
    results = await app.query_service.search(query, top_k=limit)
    return format_results(results)
```

The placeholder version can return a static message until the real `KnowledgeQueryService` is wired. **Feasibility: confirmed** (Src 1 decorator API).

### 4.5 VS Code Registration

```json
{
  "servers": {
    "owlbear-knowledge": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}", "python", "-m", "mcp_knowledge"],
      "env": { "OWLBEAR_KB_PATH": "${workspaceFolder}/knowledge.db" }
    }
  }
}
```

**Feasibility: confirmed** (Src 7, pattern from mcp-python-sdk.md).

### 4.6 Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | Tool functions | Call `search_knowledge()` directly with mock `Context` |
| Unit | Lifespan | Test `app_lifespan` yields valid `AppContext` with temp DB |
| Integration | MCP protocol | Use `mcp.server.fastmcp.testing` (undocumented but used in Qdrant server) |
| Manual | VS Code | Start server, verify tool appears in Copilot tool list |

The Qdrant MCP server (Src 2) tests tool functions directly with mocked Qdrant client. **Feasibility: confirmed.**

## 5. Recommendation (.90 confidence)

**Proceed with #40 as scoped.** The AC is well-defined and feasible. Key implementation notes:

1. **Use `src/` layout** per monorepo-tooling.md (`src/mcp_knowledge/`)
2. **Depend on `owlbear-knowledge`** via workspace source for knowledge engine types
3. **Lifespan yields frozen dataclass** with `query_service`, `graph` fields
4. **Placeholder tool returns static string** — real implementation is a follow-up
5. **Tests mock knowledge engine** — no real SQLite/Qdrant needed for scaffold tests
6. **Env var `OWLBEAR_KB_PATH`** for database location (consistent with OWLBEAR_ prefix)

**Risk:** The `packages/` directory and root `pyproject.toml` with workspace members don't exist yet. Task #40 depends on monorepo scaffolding (which should be a separate prerequisite task or part of the same phase-1 batch).

## 6. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement real search_knowledge tool in mcp-knowledge" --priority needed --status ideation --tags "phase-2,scope:mcp,scope:knowledge" --body "## Objective\nReplace the placeholder search_knowledge tool with a real implementation using KnowledgeQueryService.\n\n## Acceptance Criteria\n- [ ] search_knowledge calls KnowledgeQueryService.search() with user query\n- [ ] Results formatted as structured text with entity names, types, and relevance scores\n- [ ] Handles empty results gracefully (returns helpful message)\n- [ ] Handles KnowledgeQueryService errors with user-friendly error messages\n- [ ] Integration test with real SQLite + mock Qdrant\n\n## Context\nDepends on #40. See docs/research/scaffold-mcp-knowledge.md."
kanban\kanban-md.exe create "Add ingest and graph tools to mcp-knowledge server" --priority important --status ideation --tags "phase-2,scope:mcp,scope:knowledge" --body "## Objective\nExtend mcp-knowledge with tools for document ingestion and graph exploration.\n\n## Acceptance Criteria\n- [ ] ingest_document tool: accepts text + optional metadata, runs IngestPipeline\n- [ ] list_entities tool: returns entities filtered by type, with pagination\n- [ ] get_stats tool: returns document count, entity count, edge count\n- [ ] Each tool has unit tests with mocked knowledge engine\n- [ ] Tool descriptions are clear and actionable for LLM consumption\n\n## Context\nDepends on search_knowledge implementation. See docs/research/scaffold-mcp-knowledge.md.\nPrior art: Qdrant MCP server has 2 tools, MCP Memory server has 8 tools."
```
