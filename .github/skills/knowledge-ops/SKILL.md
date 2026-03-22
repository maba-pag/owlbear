---
name: knowledge-ops
description: Query, ingest, and manage the knowledge base (graph + vector store). Use when the agent needs to search for information, add documents, register sources, refresh content, or manage bookmarks. Covers 8 tools across 3 toolsets (knowledge, knowledge_source, bookmark).
---

# knowledge-ops

> **Agent status:** Utility skill — not dispatched by the orchestrator pipeline.
> Available to any agent or VS Code chat participant that needs knowledge-base
> operations.

Operate the hybrid knowledge base (SQLite graph + Qdrant vectors).

## Rules

- Always set `scope` to `project:{id}` when a project is active; use `global` otherwise.
- Use `query_knowledge` before ingesting — avoid duplicates.
- Prefer `doc_type='url'` over manually fetching + `doc_type='text'` when a URL exists.
- `config_json` must be valid JSON as a **string**, not a dict.
- File paths in `ingest_document(doc_type='file')` are workspace-relative and sandboxed.

## Decision Tree

| I want to… | Tool | Toolset |
|---|---|---|
| Search the knowledge base | `query_knowledge` | knowledge |
| Ingest raw text | `ingest_document` (doc_type=`text`) | knowledge |
| Ingest a local file | `ingest_document` (doc_type=`file`) | knowledge |
| Ingest from a URL | `ingest_document` (doc_type=`url`) | knowledge |
| List ingested documents | `list_knowledge_sources` | knowledge |
| Register a new source | `add_source` | knowledge_source |
| List registered sources | `list_sources` | knowledge_source |
| Trigger a source refresh | `refresh_source` | knowledge_source |
| Evaluate + bookmark a URL | `bookmark_source` | bookmark |
| List saved bookmarks | `list_bookmarks` | bookmark |

## Tool Reference

### knowledge toolset

**query_knowledge** — Search for relevant information.

| Param | Type | Default | Notes |
|---|---|---|---|
| `query` | str | required | Natural-language search query |
| `top_k` | int | 5 | Max results to return |

**ingest_document** — Add a document to the knowledge base.

| Param | Type | Default | Notes |
|---|---|---|---|
| `source` | str | required | Text content, workspace-relative path, or URL |
| `doc_type` | str | `text` | `text`, `file`, or `url` |

**list_knowledge_sources** — List all ingested documents. No parameters.

### knowledge_source toolset

**add_source** — Register a recurring knowledge source.

| Param | Type | Default | Notes |
|---|---|---|---|
| `name` | str | required | Human-readable source name |
| `source_type` | str | required | `url_list`, `crawl`, or `file_glob` |
| `config_json` | str | required | JSON string with source config |
| `scope` | str | `global` | `global` or `project:{id}` |

**list_sources** — List registered sources.

| Param | Type | Default | Notes |
|---|---|---|---|
| `scope` | str | None | Filter by scope; omit for all |

**refresh_source** — Re-fetch and ingest content from a source.

| Param | Type | Default | Notes |
|---|---|---|---|
| `name` | str | required | Name of the source to refresh |

### bookmark toolset

**bookmark_source** — Evaluate a URL for relevance and save as bookmark.

| Param | Type | Default | Notes |
|---|---|---|---|
| `url` | str | required | URL to evaluate |
| `reason` | str | None | Optional reason for bookmarking |

**list_bookmarks** — List saved bookmarks.

| Param | Type | Default | Notes |
|---|---|---|---|
| `tag` | str | None | Filter by tag |
| `min_score` | float | None | Minimum relevance score |

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
