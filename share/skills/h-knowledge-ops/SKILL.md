---
name: h-knowledge-ops
description: "Handbook: Knowledge base operations — search, ingest, and manage via MCP"
user-invocable: false
---

# Knowledge Base Operations

Tool reference and recipes for the `ob-knowledge` MCP server, registered in `.vscode/mcp.json` as `ob-knowledge`.

## Tool Reference

### search_knowledge

Search the knowledge base for relevant context.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `query` | str | required | Natural-language search query |
| `limit` | int | 5 | Max results to return |
| `scopes` | list[str] \| null | null | Scope filter (e.g. `["global", "project:myproj"]`) |

Returns: `list[dict]` — `[{"title": str, "score": float, "snippet": str}, ...]`; `[]` if no results; error string if service unavailable.

### ingest_document

Ingest a text document into the knowledge base.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `text` | str | required | Text content to ingest |
| `metadata` | dict | None | Optional metadata dict |

Returns: document ID, chunk count, entity count, edge count, and status.

### list_entities

List entities in the knowledge graph.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `entity_type` | str | None | Filter by entity type |
| `offset` | int | 0 | Pagination offset |
| `limit` | int | 50 | Max results |

Returns: `list[dict]` — `[{"name": str, "entity_type": str, "description": str}, ...]`; `[]` if no results; error string if invalid `entity_type`.

### list_sources

List all registered knowledge sources.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `scope` | str | None | Filter by scope; omit for all |

Returns: `list[dict]` — `[{"name": str, "source_type": str, "scope": str}, ...]`; `[]` if no sources.

### get_stats

Get knowledge base summary statistics. No parameters.

Returns: `dict[str, int]` — `{"documents": int, "entities": int, "edges": int}`

**Resource:** `knowledge://stats` — same format as `get_stats`, readable as MCP resource.

### get_next_batch

Atomically claim a batch of chunks ready for Phase 1 enrichment.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `limit` | int | 10 | Maximum chunks to claim |

Returns: `list[dict]` — `[{"chunk_id": str, "text": str, "doc_title": str, "section_path": str | null, "source_name": str | null}, ...]`.

Behavior:

- Claims pending chunks, plus stale claimed chunks whose lease is older than 10 minutes.
- Excludes chunks from sources with enrichment disabled.
- Updates claimed chunks inside an immediate SQLite transaction.
- Empty list means no Phase 1 work is currently available.

### get_consolidation_candidates

Return unresolved cross-source entity pairs for Phase 2 consolidation.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `limit` | int | 20 | Maximum candidates to return; omit or pass null for no SQL limit |

Returns: `list[dict]` — `[{"candidate_id": str, "entity_name": str, "source_a": str, "source_b": str, "source_a_name": str, "source_b_name": str, "source_a_chunk": str, "source_b_chunk": str}, ...]`.

Empty list means no Phase 2 consolidation work is currently available.

### store_enrichment

Persist Phase 1 extraction results or Phase 2 consolidation outcomes.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `chunk_id` | str | None | Required for Phase 1 chunk enrichment |
| `entities` | list[dict] | None | Entities to upsert for Phase 1 |
| `edges` | list[dict] | None | Edges to insert for Phase 1 or Phase 2 |
| `candidate_id` | str | None | Required for Phase 2 consolidation persistence |

Returns: `None` on success.

Behavior:

- Phase 1: pass `chunk_id` with optional `entities` and `edges`; the chunk is marked `enriched` and its claim is cleared.
- Phase 2: pass `candidate_id`; if `edges` is non-empty, the edges are stored. If no edges are needed, the pair is marked reviewed so it is not returned again.
- If neither `candidate_id` nor `chunk_id` is provided, the tool raises `ToolError`.

### bookmark_source

Bookmark a URL for evaluation and optional ingestion.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `url` | str | required | URL to bookmark |
| `reason` | str | None | Why this URL is relevant |

Returns: status string describing outcome (bookmarked, ingested, or error).

### list_bookmarks

List bookmarked URLs with optional filters.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `tag` | str | None | Filter by tag |
| `min_score` | float | None | Minimum relevance score |

Returns: `list[dict]` — bookmark entries with URL, title, tags, and score.

### import_scope

Import a project-local knowledge base into the global scope.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `project_name` | str | required | Project name to import from |
| `path` | str | None | Custom path to project DB |

Returns: status string with import counts.

### export_scope

Export a scope to a portable SQLite file.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `scope` | str | required | Scope to export |
| `output_path` | str | required | Path for the output SQLite file |

Returns: status string with export counts.

## Decision Tree

| I want to... | Tool | Notes |
|--------------|------|-------|
| Search the knowledge base | `search_knowledge` | Natural-language query, returns ranked snippets |
| Ingest a document | `ingest_document` | Pass text content + optional metadata |
| List entities in graph | `list_entities` | Filter by `entity_type`, supports pagination |
| List registered sources | `list_sources` | Filter by `scope` |
| Get KB statistics | `get_stats` | Also available as resource `knowledge://stats` |
| Claim Phase 1 enrichment work | `get_next_batch` | Pulls and leases chunks atomically |
| Store Phase 1 enrichment | `store_enrichment` | Pass `chunk_id`; marks chunk enriched |
| Claim Phase 2 consolidation work | `get_consolidation_candidates` | Returns unresolved cross-source pairs |
| Store Phase 2 consolidation | `store_enrichment` | Pass `candidate_id`; stores edges or marks reviewed |
| Bookmark a URL | `bookmark_source` | Evaluate relevance, optionally ingest |
| List bookmarks | `list_bookmarks` | Filter by `tag` or `min_score` |
| Import project KB | `import_scope` | Cross-DB scope import with dedup |
| Export scope | `export_scope` | Portable SQLite export |

## Scope Conventions

| Scope | Format | When to use |
|-------|--------|-------------|
| Global | `global` | Default. Cross-project knowledge. |
| Project | `project:{id}` | When a project is active. Auto-set by toolset constructors. |

Queries auto-filter to `["global", "project:{id}"]` when a project is active.

## Domain Reference

**EntityType:** `file`, `function`, `class_`, `decision`, `pattern`, `concept`

**RelationType:** `defines`, `imports`, `depends_on`, `related_to`, `implements`, `documents`, `governed_by`

**SourceType:** `url_list`, `file_glob`

Config examples per source type:

```json
// url_list — list of URLs to fetch
{"urls": ["https://example.com/page1", "https://example.com/page2"]}

// file_glob — workspace-relative glob pattern
{"pattern": "docs/**/*.md"}
```

## Ingest Recipes

### Check-then-ingest (avoid duplicates)

```python
results = search_knowledge(query="retry logic patterns")
if not results:
    ingest_document(text=content, metadata={"source": ".owlbear/research/retry.md"})
```

### Delta checking

The pipeline deduplicates by content hash. Re-ingesting the same content is a no-op.

## Curation Lifecycle

Six-step process for adding, updating, and removing knowledge sources. See `.owlbear/research/kb-curation-process.md` for the complete guide.

1. **Register** — track where content comes from (source metadata)
2. **Check delta** — content-hash comparison skips unchanged documents
3. **Ingest** — `ingest_document` to chunk, extract entities, and store
4. **Track status** — pipeline records ingestion state and content hash
5. **Verify** — `search-knowledge` to spot-check search relevance
6. **Remove stale** — delete source + cascade to clean up decommissioned content

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OWLBEAR_KB_PATH` | `store/knowledge/knowledge.db` | Path to SQLite knowledge database |
| `KNOWLEDGE_TOOLS_EXCLUDE` | _(unset)_ | Comma-separated tool names to remove |

`KNOWLEDGE_TOOLS_EXCLUDE` accepts: `search_knowledge`, `ingest_document`, `list_entities`, `list_sources`, `get_stats`, `bookmark_source`, `list_bookmarks`, `import_scope`, `export_scope`. Unknown names silently ignored.

## Known Gotchas

- **Always set `scope`** to `project:{id}` when a project is active; use `global` otherwise.
- **`config_json` must be valid JSON as a string**, not a dict.
- **Search before ingesting** to avoid duplicates — the dedup is by content hash, not by topic.
