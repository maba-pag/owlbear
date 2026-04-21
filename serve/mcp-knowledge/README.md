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
| `ingest_document` | Ingest a document (file path or URL) into the knowledge base |
| `list_entities` | List knowledge-graph entities, optionally filtered by type |
| `get_stats` | Summary statistics (document count, entity count, edge count) |
| `bookmark_source` | Evaluate a URL and optionally ingest it as a bookmark |
| `list_bookmarks` | List bookmarks, optionally filtered by tag or minimum score |
| `update_bookmark_tags` | Update tags on an existing bookmark |
| `import_scope` | Import a project-local knowledge snapshot into the global KB |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OWLBEAR_LOCAL_KB_PATH` | — | Path to the local SQLite knowledge database (takes precedence) |
| `OWLBEAR_KB_PATH` | `.owlbear/knowledge/local.db` | Fallback KB path |
| `OWLBEAR_LLM_API_KEY` | — | LLM API key for entity extraction (takes precedence over `OPENAI_API_KEY`) |
| `OPENAI_API_KEY` | — | OpenAI-compatible API key fallback |
| `OWLBEAR_LLM_MODEL` | `gpt-4o-mini` | LLM model name for entity extraction |
| `OWLBEAR_LLM_BASE_URL` | — | LLM base URL (takes precedence over `OPENAI_BASE_URL`) |
| `OPENAI_BASE_URL` | — | OpenAI-compatible base URL fallback |
| `KNOWLEDGE_TOOLS_EXCLUDE` | _(none)_ | Comma-separated tool names to remove at startup |

Entity extraction (and bookmarking with evaluation) requires an LLM API key. The server starts without one but extraction-dependent features degrade gracefully.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `owlbear-knowledge[full]` | Knowledge engine with all optional extras (workspace package) |
