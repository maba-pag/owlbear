---
name: knowledge-ops
description: Query, ingest, and manage the knowledge base (graph + vector store). Use when the agent needs to search for information, add documents, register sources, refresh content, or manage bookmarks. Covers 8 tools across 3 toolsets (knowledge, knowledge_source, bookmark).
---

# knowledge-ops

> **VS Code agent note:** This skill documents both the **owlbear-knowledge MCP server tools**
> (available in VS Code Copilot agent mode via `.vscode/mcp.json`) and the OwlBear PydanticAI
> runtime tools (KnowledgeToolset, KnowledgeSourceToolset, BookmarkToolset).

## MCP Server Tools (owlbear-knowledge)

The `owlbear-knowledge` MCP server exposes the knowledge base via stdio transport.
Register it in `.vscode/mcp.json` to use in Copilot agent mode.

### MCP Tool Reference

**search_knowledge** — Search the knowledge base for relevant context.

| Param | Type | Default | Notes |
|---|---|---|---|
| `query` | str | required | Natural-language search query |
| `limit` | int | 5 | Max results to return |

Returns: `list[dict]` — `[{"title": str, "score": float, "snippet": str}, ...]`; `[]` if no results; error string if service unavailable.

**ingest_document** — Ingest a text document into the knowledge base.

| Param | Type | Default | Notes |
|---|---|---|---|
| `text` | str | required | Text content to ingest |
| `metadata` | dict | None | Optional metadata dict |

**list_entities** — List entities in the knowledge graph.

| Param | Type | Default | Notes |
|---|---|---|---|
| `entity_type` | str | None | Filter by entity type |
| `offset` | int | 0 | Pagination offset |
| `limit` | int | 50 | Max results |

Returns: `list[dict]` — `[{"name": str, "entity_type": str, "description": str}, ...]`; `[]` if no results; error string if invalid `entity_type`.

**list_sources** — List all registered knowledge sources.

| Param | Type | Default | Notes |
|---|---|---|---|
| `scope` | str | None | Filter by scope; omit for all |

Returns: `list[dict]` — `[{"name": str, "source_type": str, "scope": str}, ...]`; `[]` if no sources.

**get_stats** — Get knowledge base summary statistics. No parameters.
Returns: `dict[str, int]` — `{"documents": int, "entities": int, "edges": int}`

**Resource:** `knowledge://stats` — same format as `get_stats`, readable as MCP resource.

> **Agent status:** Utility skill — not dispatched by the orchestrator pipeline.
> Available to any agent or VS Code chat participant that needs knowledge-base
> operations.

## Rules

- Always set `scope` to `project:{id}` when a project is active; use `global` otherwise.
- Use `query_knowledge` before ingesting — avoid duplicates.
- Prefer `doc_type='url'` over manually fetching + `doc_type='text'` when a URL exists.
- `config_json` must be valid JSON as a **string**, not a dict.
- File paths in `ingest_document(doc_type='file')` are workspace-relative and sandboxed.

## Decision Tree

| I want to… | MCP tool | Notes |
|---|---|---|
| Search the knowledge base | `search_knowledge` | PydanticAI: `query_knowledge` (param `top_k` instead of `limit`) |
| Ingest text/file/URL | `ingest_document` | PydanticAI: adds `doc_type` param (`text`/`file`/`url`) and `source` instead of `text` |
| List entities in graph | `list_entities` | MCP only — filter by `entity_type`, supports pagination |
| List registered sources | `list_sources` | Same in both interfaces |
| Get KB statistics | `get_stats` | Also available as resource `knowledge://stats` |
| Register a recurring source | — | PydanticAI only: `add_source` (knowledge_source toolset) |
| Trigger source refresh | — | PydanticAI only: `refresh_source` (knowledge_source toolset) |
| Evaluate + bookmark a URL | — | PydanticAI only: `bookmark_source` (bookmark toolset) |
| List saved bookmarks | — | PydanticAI only: `list_bookmarks` (bookmark toolset) |

MCP tools are the primary interface (VS Code agents). PydanticAI toolsets (KnowledgeToolset, KnowledgeSourceToolset, BookmarkToolset) are the runtime interface — see the MCP Tool Reference above for shared parameter details.

## Scope Conventions

| Scope | Format | When to use |
|---|---|---|
| Global | `global` | Default. Cross-project knowledge. |
| Project | `project:{id}` | When a project is active. Auto-set by toolset constructors. |

Queries auto-filter to `["global", "project:{id}"]` when `project_scope` is set.

## Domain Reference

**EntityType:** `file`, `function`, `class_`, `decision`, `pattern`, `concept`

**RelationType:** `defines`, `imports`, `depends_on`, `related_to`, `implements`, `documents`, `governed_by`

**SourceType:** `url_list`, `crawl`, `file_glob`

Config examples per source type:

```json
// url_list — list of URLs to fetch
{"urls": ["https://example.com/page1", "https://example.com/page2"]}

// crawl — start URL + depth
{"start_url": "https://docs.example.com", "max_depth": 2}

// file_glob — workspace-relative glob pattern
{"pattern": "docs/**/*.md"}
```

## Ingest Workflow

1. **Check first:** `query_knowledge("topic")` — avoid re-ingesting existing content.
2. **Ingest:** Choose the right `doc_type`:
   - `text` — raw content string (e.g., conversation notes, summaries)
   - `file` — workspace-relative path (sandboxed to workspace root)
   - `url` — fetches and extracts content from the URL
3. **Result:** Returns document ID, chunk count, entity count, edge count, and status.
4. **Delta checking:** The pipeline deduplicates by content hash. Re-ingesting the same content is a no-op.

For recurring sources, prefer `add_source` + `refresh_source` over repeated `ingest_document` calls.

## Curation Workflow

Full lifecycle for adding, updating, and removing knowledge sources. See [docs/research/kb-curation-process.md](../../docs/research/kb-curation-process.md) for the complete guide with worked examples and manifest format.

Six-step process:

1. **Register** — `add_source` to track where content comes from
2. **Check delta** — `StatusStore.check_content_changed()` skips unchanged documents (SHA-256 hash)
3. **Ingest** — `ingest_document` or `refresh_source` to chunk, extract, and store
4. **Track status** — pipeline records ingestion state and content hash
5. **Verify** — `query_knowledge` to spot-check search relevance
6. **Remove stale** — delete source + cascade to clean up decommissioned content

## Configuration

The `owlbear-knowledge` MCP server reads the following environment variables at startup:

| Variable | Default | Description |
|----------|---------|-------------|
| `OWLBEAR_KB_PATH` | `data/knowledge/knowledge.db` | Path to the SQLite knowledge database |
| `OWLBEAR_MODEL` | `gpt-4o-mini` | LLM model used by the entity extractor |
| `KNOWLEDGE_TOOLS_EXCLUDE` | _(unset)_ | Comma-separated list of tool names to remove from the server |

### KNOWLEDGE_TOOLS_EXCLUDE

Set this variable to hide specific tools from the MCP server. This is useful when a client
should only have access to a subset of knowledge operations (e.g., query-only access).

**Syntax:** comma-separated tool names, whitespace around names is stripped.

```
KNOWLEDGE_TOOLS_EXCLUDE=ingest_document,list_entities
```

Valid names: `search_knowledge`, `ingest_document`, `list_entities`, `list_sources`.

Unknown names are silently ignored. If the variable is not set or is empty, all tools
are registered (backwards-compatible default).
