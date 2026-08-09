# owlbear-memory-mcp — Memory MCP Server

MCP server for agent institutional memory. Pipeline and ideation agents record learnings after tasks; a dedicated curator agent reviews, scopes, and promotes entries; the human operator approves. Approved entries surface during agent pre-flight via `recall_memory`.

Storage is file-based: each entry is a markdown file with YAML frontmatter in `.owlbear/memory/`. The MCPServer app name and VS Code registration key are both `owlbear-memory`.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
uv run python -m owlbear_memory_mcp
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json` — not invoked directly.

## Architecture

### Modules

| Module | Purpose |
|--------|---------|
| `agents.py` | Dynamic canonical-agent discovery from active VS Code agent locations |
| `server.py` | MCPServer app definition, tool registration, lifespan wiring |
| `tools.py` | Tool implementation — validation, state transitions, response formatting |
| `git.py` | Batch commit helper — stages non-pending entries by session type |
| `__main__.py` | Entry point for `python -m owlbear_memory_mcp` |

Engine and model types (`MemoryEngine`, `MemoryEntry`, `MemoryCategory`, `MemoryState`, error types) are provided by the `owlbear-memory` workspace package.

### State Model

Entries follow a curated-approval lifecycle:

```
pending ──[curate with scope]──► curated ──[approve]──► approved
   │                               │  ▲                    │
   │                               │  └──[curate edit]─────┘
   └──[delete: hard]               └──[delete: soft → deleted]

contested ──[resolve*]──► approved    [delete: soft → deleted]
disputed  ──[resolve*]──► approved    [delete: soft → deleted]
stale     ──[resolve*]──► approved    [delete: soft → deleted]

* resolve() is a MemoryEngine method; no MCP tool is exposed. Cockpit is the human editing and resolution surface for contested, disputed, and stale entries.
```

- **pending** → invisible to `recall_memory`, not committed to git
- **curated** → visible to scoped agents, committable
- **approved** → highest-trust retrieval priority, committable
- **contested** → visible to `recall_memory` (rank = curated); `curate_memory` (edit) blocked; delete soft-deletes
- **disputed** → excluded from `recall_memory`; `curate_memory` (edit) blocked; delete soft-deletes
- **stale** → excluded from `recall_memory`; `curate_memory` (edit) blocked; delete soft-deletes
- **deleted** → soft-deleted (curated/approved/contested/disputed/stale) or hard-deleted from disk (pending)

## Tools

| Tool | Description |
|------|-------------|
| `save_memory` | Create an unscoped `pending` entry from an active canonical agent identity |
| `list_memories` | List metadata sorted by curation priority; filters: `states`, `categories`, `scope_agents` |
| `read_memory` | Read one full entry by `entry_id`; errors on deleted entries |
| `recall_memory` | Identity-bearing markdown blocks scoped to one agent (`## title`, entry ID, and body on consecutive lines; other metadata omitted); three-pool slot allocation (explore, challenge, regular) with final sort by `(state_rank, -score, id)`; constants `SLOT_EXPLORE=2`, `SLOT_CHALLENGE=2`; default limit 20 |
| `curate_memory` | Mutate fields + auto-promote `pending→curated` (when scope provided) or auto-downgrade `approved→curated`; raises `TransitionError` for contested/disputed/stale (use resolve first) |
| `delete_memory` | Hard-delete pending (file removed); soft-delete curated/approved/contested/disputed/stale (state→deleted) |
| `rename_agent_memories` | Rewrite every matching `source_agent` and `scope_agents` reference after an agent rename |
| `delete_agent_memories` | Preserve historical provenance, remove the retired role from scopes, and physically delete entries left without an audience |
| `approve_memory` | Promote `curated→approved`; user-initiated only (not exposed to any agent) |
| `assess_memories` | Process batch assessment submissions; increments counters for `outstanding`/`unremarkable`/`didnt_use`, delegates `factually_wrong` to confirmation cycle; returns per-entry `{entry_id, success}` or `{entry_id, success=False, error}` results |

All mutating tools return a `hint` field describing the transition or action taken.

## Entry Schema

| Field | Type | Constraint |
|-------|------|------------|
| `id` | str | Stable UUID identifier |
| `title` | str | Required, non-empty |
| `content` | str | Markdown body (max 1024 chars at MCP layer) |
| `categories` | list[str] | One or more from: `domain-knowledge`, `behaviour`, `pitfall`, `process`, `tool-usage`, `goal`, `personality`, `preference`, `env-context` |
| `confidence` | float | `[0.7, 1.0]` inclusive |
| `state` | str | `pending` (default), `curated`, `approved`, `contested`, `disputed`, `stale`, `deleted` |
| `outstanding_count` | int | Default `0`; incremented by assessment tool when entry was outstanding |
| `unremarkable_count` | int | Default `0`; incremented by assessment tool when entry was unremarkable |
| `didnt_use_count` | int | Default `0`; incremented by assessment tool when entry was skipped |
| `score` | float | Default `0.0`; initialized to `confidence` on creation |
| `source_agent` | str | Active custom-agent name required at creation; immutable historical provenance except through an explicit lifecycle rename |
| `scope_agents` | list[str] | Curator-assigned relevance scope; new pending entries default to `[]` |
| `created_at` | str | UTC timestamp |
| `updated_at` | str | UTC timestamp |
| `approved_at` | str \| null | Set on approve, cleared on downgrade/delete |
| `contested_by_task` | str \| null | Task ID of the first factually-wrong confirmation; null until first confirmation; cleared on resolve |

## Agent Identity

The server discovers exact frontmatter names from `.github/agents`, `.owlbear/agents`, `share/agents`,
and enabled `chat.agentFilesLocations` in workspace settings. Identity is self-reported by the
caller and validated as vocabulary, not authenticated as an authorization boundary. Scope controls
relevance filtering only.

Rename memory references with `rename_agent_memories`. When deleting an agent,
`delete_agent_memories` preserves immutable source provenance, removes the retired identity from
relevance scopes, and deletes only entries left without an audience. No aliases or retired role
names remain in active relevance scope.

## Configuration

Memory entries are stored at `.owlbear/memory` under the current initialized workspace. The server
has no environment configuration.

## Batch Commits

Pending entries are intentionally left uncommitted. After curation or review, commit only reviewed entries with the state-aware helper:

```bash
uv run python -m owlbear_memory_mcp.git curation
uv run python -m owlbear_memory_mcp.git review
```

The `--project` path must point to the OwlBear installation root. Find the correct value from the `owlbear-memory` server entry in `.vscode/mcp.json` (look for the `--project` argument in the `args` array). Example:

```bash
uv --project ../owlbear run python -m owlbear_memory_mcp.git review
```

The helper stages only non-pending `.owlbear/memory/*.md` files and returns the commit SHA, or `no memory changes to commit` when there is nothing to commit.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | MCPServer framework and CLI |
| `owlbear-memory` | Shared memory engine, models, and error types (workspace package) |
| `pydantic` | Model validation at the MCP tool layer |
| `pyyaml` | YAML frontmatter serialisation for memory files |
