---
name: knowledge-ops
description: Query, ingest, and manage the knowledge base (graph + vector store) via the owlbear-knowledge MCP server. Covers search, ingestion, entity listing, source management, and statistics.
---

# knowledge-ops

> **Scope:** This skill documents the **owlbear-knowledge MCP server** tools,
> registered in `.vscode/mcp.json` as `owlbear-knowledge`.

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
- Use `search_knowledge` before ingesting — avoid duplicates.
- `config_json` must be valid JSON as a **string**, not a dict.

## Decision Tree

| I want to… | MCP tool | Notes |
|---|---|---|
| Search the knowledge base | `search_knowledge` | Natural-language query, returns ranked snippets |
| Ingest a document | `ingest_document` | Pass text content + optional metadata |
| List entities in graph | `list_entities` | Filter by `entity_type`, supports pagination |
| List registered sources | `list_sources` | Filter by `scope` |
| Get KB statistics | `get_stats` | Also available as resource `knowledge://stats` |

## Scope Conventions

| Scope | Format | When to use |
|---|---|---|
| Global | `global` | Default. Cross-project knowledge. |
| Project | `project:{id}` | When a project is active. Auto-set by toolset constructors. |

Queries auto-filter to `["global", "project:{id}"]` when a project is active.

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

1. **Check first:** `search_knowledge("topic")` — avoid re-ingesting existing content.
2. **Ingest:** Use `ingest_document` with text content and optional metadata.
3. **Result:** Returns document ID, chunk count, entity count, edge count, and status.
4. **Delta checking:** The pipeline deduplicates by content hash. Re-ingesting the same content is a no-op.

## Curation Workflow

Full lifecycle for adding, updating, and removing knowledge sources. See [docs/research/kb-curation-process.md](../../docs/research/kb-curation-process.md) for the complete guide with worked examples and manifest format.

Six-step process:

1. **Register** — track where content comes from (source metadata)
2. **Check delta** — content-hash comparison skips unchanged documents
3. **Ingest** — `ingest_document` to chunk, extract entities, and store
4. **Track status** — pipeline records ingestion state and content hash
5. **Verify** — `search_knowledge` to spot-check search relevance
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
