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
| `knowledge_search` | Semantic search over the knowledge base |
| `knowledge_entity_lookup` | Look up a graph entity and its neighbourhood by `entity_id`, `entity_name`, or `entity_type`; expands the graph by `expand_hops` hops (default 1); returns `entity`, `neighbourhood` (entities + edges), and `related_chunks` |
| `knowledge_sources_list` | List registered knowledge sources, optionally filtered by scope |
| `knowledge_ingest` | Ingest text content into the knowledge base using a per-scope shared inline source (`mcp-inline-{scope}`); `source_url` stored as document URI; response includes `documents_processed`, `chunks_created`, and `chunks_enqueued` |
| `get_consolidation_candidates` | List unresolved cross-source entity consolidation candidates (entities appearing in 2+ sources with no existing edge or reviewed dismissal) |

> **TODO:** stale — `get_consolidation_candidates` was retired per CP1; this row should be removed and the package description updated to remove "consolidation candidate review" once the retired tool is confirmed purged from server.py

| `knowledge_stats` | Summary statistics: document, entity, and edge counts plus source count, chunk count, enrichment ratio, and consolidation candidates remaining |
| `knowledge_sources_refresh` | Re-ingest a registered source by source ID; response includes `source_id` (echoed), `sources_refreshed` (int), and `errors` (list of `{source_id, error, timestamp}` entries); raises `ToolError` when source is not found; returns error envelope when source is not active |
| `knowledge_sources_delete` | Delete a source and all its associated data (vectors, documents, chunks, entities, enrichment) via coordinator-orchestrated purge; returns a purge-result summary with status (`complete`/`partial`), completed steps, failed step, error, and per-domain sub-results (source, content, enrichment, graph) |
| `knowledge_enrichment_claim_batch` | Atomically claim a batch of chunks ready for enrichment |
| `knowledge_enrichment_store` | Dual-mode enrichment persist: Phase 1 (`chunk_id`, `entities`, `edges`) marks chunk enriched; Phase 2 (`candidate_id`, `edges`) writes cross-source edges or records a reviewed-pair dismissal |
| `knowledge_enrichment_retry` | Reset failed enrichment chunks to pending so workers can retry them |
| `knowledge_sources_register` | Register a new source in the v2 source store; accepts name, kind, fetch_method, config, scope, enrich, refreshable, priority, metadata; validates via Pydantic and returns registered record (id, name, state, kind, scope) |

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
