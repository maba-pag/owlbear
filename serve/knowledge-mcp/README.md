# owlbear-knowledge-mcp — Knowledge MCP Server

MCP server that exposes the `owlbear-knowledge` engine as tools for pipeline agents. Provides document ingestion, semantic search, source management, and enrichment batching. Registered in VS Code's MCP configuration as `owlbear-knowledge`.

**Use this guide when:** you need to configure the alpha `owlbear-knowledge` server or change its
agent-facing source, search, and enrichment tools.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

**Status:** Alpha. The server exposes the current Knowledge tool surface, but end-to-end
real-world validation is still pending.

---

## Launch / Usage

```bash
uv run python -m owlbear_knowledge_mcp
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json`.

### Tools

| Tool | Description |
| --- | --- |
| `knowledge_search` | Semantic search over the knowledge base; returns a result list on success or a typed query failure with `stage`, `code`, `retryable`, and `message` fields |
| `lookup_knowledge_entity` | Look up a graph entity and its neighbourhood by `entity_id`, `entity_name`, or `entity_type`; expands the graph by `expand_hops` hops (default 1); returns `entity`, `neighbourhood` (entities + edges), and `related_chunks` |
| `list_knowledge_sources` | List registered knowledge sources, optionally filtered by scope |
| `knowledge_ingest` | Ingest text content into the knowledge base using a per-scope shared inline source (`mcp-inline-{scope}`); `source_url` stored as document URI; response includes `documents_processed`, `chunks_created`, and `chunks_enqueued` |
| `knowledge_stats` | Summary statistics: document, entity, edge, source, and chunk counts plus enrichment queue state and completion ratio |
| `refresh_knowledge_source` | Re-ingest a registered source by source ID; response includes retained `source_id`, `sources_refreshed`, and structured `errors` fields plus additive `documents_created`, `documents_replaced`, `documents_unchanged`, `chunks_created`, and `chunks_replaced` counts; raises `ToolError` for unknown or inactive sources |
| `delete_knowledge_source` | Delete a source and all its associated data (vectors, documents, chunks, entities, enrichment) via coordinator-orchestrated purge; returns a purge-result summary with status (`complete`/`partial`), completed steps, failed step, error, and per-domain sub-results (source, content, enrichment, graph) |
| `claim_enrichment_batch` | Atomically claim a batch of chunks ready for enrichment |
| `store_enrichment` | Persist extracted entities and local-reference edges for a claimed chunk, then mark it enriched |
| `retry_enrichment` | Reset failed enrichment chunks to pending so workers can retry them |
| `register_knowledge_source` | Register a new source in the v2 source store; accepts name, kind, fetch_method, config, scope, enrich, refreshable, priority, metadata; validates via Pydantic and returns registered record (id, name, state, kind, scope) |

### Response shapes

`knowledge_search` returns the existing list of search result objects when the query succeeds.
When query embedding or vector retrieval fails, it returns one redacted `KnowledgeFailure`
projection:

```json
{
  "stage": "query",
  "code": "vector_query_failed",
  "retryable": true,
  "message": "Vector search failed"
}
```

`refresh_knowledge_source` always retains its source and additive outcome fields. Each item in
`errors` is a structured refresh failure with `source_id`, `stage`, `code`, `retryable`,
`message`, and `timestamp` fields. A successful no-op refresh has `sources_refreshed: 1`, all
document and chunk counts set to `0`, and an empty `errors` list. For a URL-list source with one
successful and one failed URL, successful document and chunk counts remain present, the source is
counted as refreshed, and the failed item is represented in `errors`.

Use `stage`, `code`, and `retryable` as structured failure fields; `message` is a redacted,
human-readable description. Unknown or inactive sources, and unavailable store, coordinator, or
query-service dependencies, raise `ToolError` with a safe precondition message rather than adding
an item to `errors` or returning a query failure projection.

## Configuration

Knowledge storage is fixed to `.owlbear/knowledge/local.db` and
`.owlbear/knowledge/vectors` under the current workspace. The server must be launched from an
initialized OwlBear workspace and exposes its complete tool set.

The server's private composition root assembles the SQLite stores, content and query facades,
ingest coordinator, and composite source fetcher. Production lifespan wiring supplies zero-argument
HTTP response-fetcher and BGE-M3 embedding factories plus a filesystem Qdrant factory. Deterministic assembled
tests replace only those lower runtime factories, keeping source registration, SSRF validation,
SQLite persistence, and MCP tool calls on the same path as production.

## Dependencies

| Package | Purpose |
| --- | --- |
| `mcp` | MCPServer framework |
| `owlbear-knowledge[full]` | Knowledge engine with Qdrant, BGE-M3 embeddings, and HTTP intake (workspace package) |
