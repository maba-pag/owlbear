# owlbear-mcp-memory — Memory MCP Server

MCP server that provides agent institutional memory via a file-based store. Agents record learnings, retrieve relevant knowledge, and curate entries through an approval workflow. Registered in VS Code's MCP configuration as `owlbear-memory`.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
uv run python -m owlbear_mcp_memory
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json`.

### Tools

| Tool | Description |
|------|-------------|
| `store_learning` | Create a new `pending` memory entry |
| `query_memory` | Retrieve entries by state (`curated` and `approved` by default), approved-first then confidence-desc; supports optional `categories`, `scope_agents`, `min_confidence`, and `limit` filters (AND semantics) |
| `update_entry` | Curator-only updates; supports `pending -> curated` and blocks modifications of `approved` entries |
| `delete_entry` | Curator-only soft delete to `deleted` state |
| `approve_entry` | User-only promotion from `curated -> approved` |

### Entry schema

Entries are scoped to an optional agent (`scope_agents` list). Valid categories: `knowledge`, `behaviour`, `pitfall`, `process`, `tool`, `goal`, `personality`, `preference`, `context`. Confidence must be in [0.7, 1.0]. States: `pending` (default), `curated`, `approved`, `deleted`.

## Configuration

| Variable | Default | Purpose |
|----------|---------|--------|
| `OWLBEAR_MEMORY_DIR` | `.owlbear/memory` | Directory for markdown memory files |
| `OWLBEAR_MEMORY_CALLER` | `unknown` | Caller identity used for access-control checks |
| `MEMORY_TOOLS_EXCLUDE` | — | Comma-separated tool names to remove from this server instance |

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `pydantic` | Model validation |
| `pyyaml` | YAML frontmatter serialisation for memory files |
