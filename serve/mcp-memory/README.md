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
| `query_memory` | Retrieve entries by state (`curated` and `approved` by default), approved-first then confidence-desc |
| `update_entry` | Curator-only updates; supports `pending -> curated` and blocks modifications of `approved` entries |
| `delete_entry` | Curator-only soft delete to `deleted` state |
| `approve_entry` | User-only promotion from `curated -> approved` |

### Entry schema

Entries are scoped to an optional agent (`scope_agents` list). Valid categories: `knowledge`, `behaviour`, `pitfall`, `process`, `tool`, `goal`, `personality`, `preference`, `context`. Confidence must be in [0.7, 1.0]. States: `pending` (default), `curated`, `approved`, `deleted`.

## Configuration

The server is being rebuilt with a file-based store (markdown files with YAML frontmatter, default location `.owlbear/memory`). Configuration env vars will be documented when the new server entry point is implemented.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `pydantic` | Model validation |
