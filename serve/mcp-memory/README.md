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
| `update_entry` | Update mutable fields; auto-promotes `pending → curated` when `scope_agents` provided (scope gate rejects if missing); auto-downgrades `approved → curated` unconditionally |
| `delete_entry` | Delete an entry; hard-deletes `pending` entries (file removed from disk); soft-deletes `curated`/`approved` entries to `deleted` state |
| `approve_entry` | Promote a `curated` entry to `approved` |
| `curate_memory` | Alias for `update_entry` — same curation semantics; returns a `hint` field describing the state transition |
| `delete_memory` | Alias for `delete_entry` — same deletion semantics; returns a `hint` field identifying hard-delete vs soft-delete |
| `recall_memory` | Retrieve body-only text for a single scoped agent; returns approved entries first then curated, filtered by `scope_agents`; supports optional `categories` and `limit` (default 20); rejects wildcard `agent="*"` |

### Entry schema

Entries are scoped to an optional agent (`scope_agents` list) and carry a required `source_agent` (set automatically from the caller identity). Valid categories: `domain-knowledge`, `behaviour`, `pitfall`, `process`, `tool-usage`, `goal`, `personality`, `preference`, `env-context`. Confidence must be in [0.7, 1.0]. States: `pending` (default), `curated`, `approved`, `deleted`.

## Configuration

| Variable | Default | Purpose |
|----------|---------|--------|
| `OWLBEAR_MEMORY_DIR` | `.owlbear/memory` | Directory for markdown memory files |

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `pydantic` | Model validation |
| `pyyaml` | YAML frontmatter serialisation for memory files |
