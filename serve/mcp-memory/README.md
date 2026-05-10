# owlbear-mcp-memory — Memory MCP Server

MCP server that provides agent institutional memory via a file-based store. Agents record learnings, retrieve relevant knowledge, and curate entries through an approval workflow. The FastMCP app name is `owlbear-memory`; VS Code registers it in `.vscode/mcp.json` as `ob-memory`.

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
| `save_memory` | Create a new `pending` memory entry with explicit `source_agent` |
| `list_memories` | List entry metadata sorted by curation priority (pending first, then by `created_at`); supports optional `states`, `categories`, and `scope_agents` filters |
| `read_memory` | Read a full memory entry by `entry_id` |
| `curate_memory` | Update mutable fields on an entry; auto-promotes `pending → curated` when `scope_agents` provided; auto-downgrades `approved → curated`; returns a `hint` describing the transition |
| `delete_memory` | Delete an entry; hard-deletes `pending` entries (file removed from disk); soft-deletes `curated`/`approved` to `deleted` state; returns a `hint` identifying the deletion type |
| `recall_memory` | Recall body-only markdown blocks for entries scoped to a specific agent; supports optional `categories` filter and `limit` (default 20); approved entries returned before curated |
| `approve_memory` | Approve a `curated` entry; returns a `hint` confirming visibility to scoped agents |

### Entry schema

Entries are scoped to an optional agent (`scope_agents` list) and carry a required `source_agent` (caller-supplied). Valid categories: `domain-knowledge`, `behaviour`, `pitfall`, `process`, `tool-usage`, `goal`, `personality`, `preference`, `env-context`. Confidence must be in [0.7, 1.0]. States: `pending` (default), `curated`, `approved`, `deleted`.

## Configuration

| Variable | Default | Purpose |
|----------|---------|--------|
| `OWLBEAR_MEMORY_DIR` | `.owlbear/memory` | Directory for markdown memory files |

## Batch Commits

Pending entries are intentionally left uncommitted. After curation or review,
commit only reviewed entries with the state-aware helper:

```bash
uv run python -m owlbear_mcp_memory.git curation
uv run python -m owlbear_mcp_memory.git review
```

From a consumer workspace that launches OwlBear via a sibling clone, use the same
project path as the `ob-memory` MCP entry, for example:

```bash
uv --project ../owlbear run python -m owlbear_mcp_memory.git review
```

The helper stages only non-pending `.owlbear/memory/*.md` files and returns the
commit SHA, or `no memory changes to commit` when there is nothing reviewed to
commit.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `pydantic` | Model validation |
| `pyyaml` | YAML frontmatter serialisation for memory files |
