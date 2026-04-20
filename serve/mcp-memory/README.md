# owlbear-mcp-memory — Memory MCP Server

MCP server that provides agent institutional memory via a SQLite-backed store. Agents record learnings, retrieve relevant knowledge, and curate entries through an approval workflow. Registered in VS Code's MCP configuration as `owlbearMemory`.

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

| Variable | Default | Description |
|----------|---------|-------------|
| `OWLBEAR_MEMORY_DB_PATH` | `store/memory/memory.db` | Path to the SQLite memory database |

The database file and parent directories are created automatically on first launch. The project name is read from `owlbear-project.json` in the working directory (used for project-scoped filtering).

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `pydantic` | Model validation |
