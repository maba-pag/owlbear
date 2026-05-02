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
| `get_knowledge` | Retrieve memory entries for an agent, sorted by scope-specificity |
| `record_learning` | Store a new memory entry with category, confidence, and scope |
| `list_entries` | List all entries (including pending and deleted) for curation |
| `set_approval_state` | Transition entry state (`pending → approved`, `pending → deleted`, `deleted → pending`) |
| `mark_for_deletion` | Soft-delete an entry by ID |

### Entry schema

Entries are scoped to an optional agent and optional project. Valid categories: `preference`, `knowledge`, `context`, `behavior`, `goal`. Confidence must be ≥ 0.7.

## Configuration

The server is being rebuilt with a file-based store (markdown files with YAML frontmatter, default location `.owlbear/memory`). Configuration env vars will be documented when the new server entry point is implemented.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `pydantic` | Model validation |
