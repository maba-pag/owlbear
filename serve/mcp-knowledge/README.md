# owlbear-mcp-knowledge — Knowledge MCP Server

MCP server that exposes the `owlbear-knowledge` engine as tools for pipeline agents. Provides document ingestion, semantic search, source management, enrichment batching, and consolidation candidate review. Registered in VS Code's MCP configuration as `owlbear-knowledge`.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
uv run python -m owlbear_mcp_knowledge
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json`.

### Tools

| Tool | Description |
|------|-------------|
| `search_knowledge` | Semantic search over the knowledge base |
| `list_sources` | List registered knowledge sources, optionally filtered by scope |
| `ingest_document` | Ingest text content into the knowledge base; `source_url` and URL-like metadata identities use content-hash delta detection and source linkage; anonymous/plain-label text creates non-refreshable inline source provenance; partial graph extraction returns warnings |
| `get_consolidation_candidates` | List unresolved cross-source entity consolidation candidates (entities appearing in 2+ sources with no existing edge or reviewed dismissal) |
| `get_stats` | Summary statistics: document, entity, and edge counts plus source count, chunk count, enrichment ratio, and consolidation candidates remaining |
| `refresh_source` | Re-ingest a registered source by source ID; response includes full, partial, skipped, failed, error, and warning counts |
| `remove_source` | Delete a source and all its associated vectors, documents, chunks, and entities; vectors are deleted first — any Qdrant failure aborts before SQLite changes |
| `get_next_batch` | Atomically claim a batch of chunks ready for enrichment |
| `store_enrichment` | Dual-mode enrichment persist: Phase 1 (`chunk_id`, `entities`, `edges`) marks chunk enriched; Phase 2 (`candidate_id`, `edges`) writes cross-source edges or records a reviewed-pair dismissal |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OWLBEAR_LOCAL_KB_PATH` | — | Path to the local SQLite knowledge database (takes precedence) |
| `OWLBEAR_KB_PATH` | `.owlbear/knowledge/local.db` | Fallback KB path |
| `OWLBEAR_QDRANT_PATH` | `.owlbear/knowledge/vectors` | Path to Qdrant vector store directory (filesystem persistence) |
| `KNOWLEDGE_TOOLS_EXCLUDE` | _(none)_ | Comma-separated tool names to remove at startup |

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `owlbear-knowledge[full]` | Knowledge engine with all optional extras (workspace package) |
