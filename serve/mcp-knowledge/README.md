# owlbear-mcp-knowledge — Knowledge MCP Server

MCP server that exposes the `owlbear-knowledge` engine as tools for pipeline agents. Provides document ingestion, semantic search, entity graph queries, bookmarking, and cross-project scope transfer. Registered in VS Code's MCP configuration as `owlbear-knowledge`.

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
| `ingest_document` | Ingest text content into the knowledge base (optional `source_url` for attribution) |
| `list_entities` | List knowledge-graph entities, optionally filtered by type |
| `get_stats` | Summary statistics (document count, entity count, edge count) |
| `bookmark_source` | Evaluate a URL and optionally ingest it as a bookmark |
| `list_bookmarks` | List bookmarks, optionally filtered by tag or minimum score |
| `update_bookmark_tags` | Update tags on an existing bookmark |
| `import_scope` | Import a project-local knowledge snapshot into the global KB |
| `export_scope` | Export all knowledge rows for one scope to a portable SQLite file |
| `sync_from_global` | Import the global knowledge DB into local scope `global` |
| `sync_to_global` | Export local scope `global` rows to the global knowledge DB |
| `refresh_source` | Re-ingest a registered source by source ID |
| `consolidate_knowledge` | Synthesize cross-document insights from unconsolidated chunks |
| `get_next_batch` | Atomically claim a batch of chunks ready for enrichment |
| `store_enrichment` | Persist extracted entities and edges, mark chunk as enriched |

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
