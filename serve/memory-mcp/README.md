# owlbear-memory-mcp — Memory MCP Server

MCP server for agent institutional memory. Pipeline and ideation agents record learnings after tasks; a dedicated curator agent reviews, scopes, and promotes entries; the human operator approves. Approved, curated and contested entries surface during agent pre-flight via `recall_memory`; Delivery's step sessions get them in their first message instead, chosen by the memory package's shared policy (`owlbear_memory.selection`), and recall when that message says they could not be read or did not fit, or for more.

Storage is file-based: each entry is a markdown file with YAML frontmatter in the memory store that
[Configuration](#configuration) describes. The MCPServer app name and VS Code registration key are both `owlbear-memory`.

**Use this guide when:** you need to change the seeded `owlbear-memory` tools, scoped retrieval, or
the human approval and curation lifecycle.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

---

## Launch / Usage

```bash
uv run python -m owlbear_memory_mcp
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json` — not invoked directly.

## Architecture

### Modules

| Module | Purpose |
| --- | --- |
| `server.py` | MCPServer app definition, tool registration, lifespan wiring |
| `tools.py` | Tool implementation — validation, state transitions, response formatting |
| `git.py` | State-aware batch commit implementation used by the MCP operation |
| `__main__.py` | Entry point for `python -m owlbear_memory_mcp` |

Engine and model types (`MemoryEngine`, `MemoryEntry`, `MemoryCategory`, `MemoryState`, error types) are provided by the `owlbear-memory` workspace package.

### State Model

Entries follow a curated-approval lifecycle:

```text
pending ──[curate with scope]──► curated ──[approve]──► approved
   │                               │  ▲                    │
   │                               │  └──[curate edit]─────┘
   └──[delete: hard]               └──[delete: soft → deleted]

contested ──[resolve*]──► approved    [delete: soft → deleted]
disputed  ──[resolve*]──► approved    [delete: soft → deleted]
stale     ──[resolve*]──► approved    [delete: soft → deleted]

* resolve() is a MemoryEngine method; no MCP tool is exposed. The Delivery engine's Memory page is the human editing and resolution surface for contested, disputed, and stale entries.
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
| --- | --- |
| `save_memory` | Create an unscoped `pending` entry from self-reported provenance and the saver's recommended scope (`where`: `project` or `global`); recognition is not authorization |
| `list_memories` | List metadata sorted by curation priority, including each entry's `revision`; filters: `states`, `categories`, `scope_agents` |
| `read_memory` | Read one full entry by `entry_id`, including its `revision`; errors on deleted entries |
| `recall_memory` | Identity-bearing markdown blocks scoped to one agent (`## title`, `Entry ID`, `Revision` immediately after the ID, then optional contested state/challenge lines and body; contested entries add one `Challenge task:` line per record); three-pool slot allocation (explore, challenge, regular) with final sort by `(state_rank, -score, id)`; constants `SLOT_EXPLORE=2`, `SLOT_CHALLENGE=2`; default limit 20 |
| `curate_memory` | Requires `revision`; mutates fields, promotes `pending→curated` when scope is provided, or downgrades `approved→curated`; raises `TransitionError` for contested/disputed/stale; refuses a named scope agent nothing vouches for (see Agent Identity) |
| `delete_memory` | Requires `revision`; hard-deletes pending entries and soft-deletes curated/approved/contested/disputed/stale entries |
| `make_global` | Curator: moves a curated or approved entry into Global memory, records its project as `origin`, and commits both paths |
| `curation_threshold` | Curator: the confidence threshold in percent from the shared repository's global settings, else 95 |
| `rename_agent_memories` | Rewrite every matching `source_agent` and `scope_agents` reference after an agent rename |
| `delete_agent_memories` | Preserve historical provenance and remove the retired role from scopes; hard-delete pending orphans and tombstone reviewed orphans for the normal commit/purge flow |
| `approve_memory` | Requires `revision` to promote `curated→approved`; user-initiated only (not exposed to any agent) |
| `assess_memories` | Process revision-bound batch assessments, applying counters or the factually-wrong confirmation cycle; each result includes `success`, `already_applied`, and `recorded_bucket` (plus `state` and `challenges` for a challenged entry), or `success=False` with `error` |
| `commit_memory_batch` | Commit non-pending memory entries for one explicit `curation` or `review` session; return the commit SHA or a no-op result, and any deferred duplicate deletions |

All mutating tools return a `hint` field describing the transition or action taken.

## Revision-bound mutations

`approve_memory`, `curate_memory`, and `delete_memory` require a `revision` from the current
`read_memory` or `list_memories` result. The 16-character lowercase hex token covers `title`,
`content`, `categories`, `confidence`, and `scope_agents`; it does not depend on `state`, assessment
counters, or timestamps. If the entry changed after it was read, the server refuses the mutation
with a tool error naming the expected and current revisions and instructing the caller to re-read
before retrying. Re-read the entry and retry with its new revision.

## Revision-Bound Assessments

Each `recall_memory` block places `Revision: {revision}` immediately after
`Entry ID:`. `assess_memories` takes a batch-level `task_id` of 1-128 printable
ASCII characters without whitespace and a non-empty `assessments` list. Each
item has exactly `{entry_id, revision, bucket}`, using the revision from the
entry's recall block.

A stale revision is refused for that entry, leaves it unchanged, and returns
an error naming the current revision. Re-recall changed content before
submitting feedback about it; do not resubmit stale feedback against content
not yet seen. Valid batches may return mixed per-entry results.

The engine stores the first bucket for each task, entry, and revision with the
entry. A repeat of the same tuple returns `success: true`,
`already_applied: true`, and the first `recorded_bucket`, without applying the
assessment again. A different task ID is independent. Receipts are retained
only for the current revision, up to 20. Oldest receipts are evicted first as
needed to keep the serialized entry within 8192 bytes while always retaining
the newest. If the newest receipt cannot fit, the assessment fails without
changing the entry, counters, or receipts. Content edits preserve counters but
remove receipts for the previous revision.

## Entry Schema

| Field | Type | Constraint |
| --- | --- | --- |
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
| `source_agent` | str | Non-blank provenance label required at creation; immutable historical provenance except through an explicit lifecycle rename |
| `scope_agents` | list[str] | Curator-assigned relevance scope; new pending entries default to `[]`; supplied members must be nonblank strings; `*` means all agents |
| `created_at` | str | UTC timestamp |
| `updated_at` | str | UTC timestamp |
| `approved_at` | str \| null | Set on approve, cleared on downgrade/delete |
| `challenges` | list of `{task_id, revision, recorded_at}` | Ordered records for the current dispute cycle; at most two; retained on delete and cleared on resolve; omitted when empty |

## Agent Identity

The server accepts every non-blank provenance label at intake, without active-agent runtime validation.
Identity is self-reported and immutable historical provenance; scope controls relevance filtering
only. `*` provenance is anonymous, and it does not establish the scope of an entry.

`curate_memory` gives an entry a named scope agent only when the server knows that agent
(`OWLBEAR_MEMORY_AGENTS`) or another curated or approved entry, in the folder or in Global memory, has it in scope;
otherwise it raises `ToolError` naming the agents and changes nothing. A pending entry's whole named scope is
checked, also when the call leaves the scope as it is; an edit of a curated or approved entry checks only the names
it adds. Provenance never vouches, and neither does the entry itself or a pending, contested, disputed, stale or
deleted entry; `*` always passes. An agent outside the known list therefore needs such a reviewed entry first.

Rename memory references with `rename_agent_memories`. When deleting an agent,
`delete_agent_memories` preserves immutable source provenance, removes the retired identity from
relevance scopes. Pending entries left without an audience are hard-deleted; reviewed entries become
`deleted` tombstones that must be committed before they are purged. No aliases or retired role names
remain in active relevance scope.

## Configuration

Delivery's steps name the store in `OWLBEAR_MEMORY_DIR` (the project's folder in the shared data repository) and
Global memory in `OWLBEAR_MEMORY_GLOBAL_DIR`, read beside it and never written; the working folder then needs no
initialized workspace. They also pass `OWLBEAR_MEMORY_AGENTS`, Delivery's roles and OwlBear's agent files
comma-separated; without it, as in a chat, the server knows no agents.

Without them, as in a chat, the server finds the shared data repository as Delivery does: `OWLBEAR_DATA` when set
(empty means none), else the machine's pointer `~/.owlbear/data.json`, else `~/.owlbear/data` when it exists. The folder whose `repository` file holds the
workspace's identity (its origin without scheme, user and `.git`) keeps its memory in `memory`, and the repository's
own `memory` is Global memory (TD-72, TD-241). A pointer or claim that cannot tell the folder stops the server with
the reason. A workspace no folder claims keeps its memory at `.owlbear/memory` in the initialized workspace.

## Writer Model and Freshness

MemoryEngine mutations and `commit_memory_batch` use one exclusive advisory lock on the resolved
memory directory. The lock coordinates threads, engine instances, and other processes, uses one
bounded wait (30 seconds by default), and creates no lock file. A timeout raises
`MemoryBusyError`, a `ConcurrencyError` subtype. MCP mutation tools surface busy and stale-token
failures as `ToolError`; a stale `revision` is checked against the fresh on-disk entry
and does not overwrite newer content.

Non-writing reads remain lock-free. `MemoryEngine.get_entries()` reparses when an entry filename,
inode, size, or `mtime_ns` changes; `load()` forces a full parse. Before each mutation, the engine
reloads under the lock and repairs duplicate IDs. Reads select or report duplicates but never
repair them. The newest copy keeps the original ID, identical copies are removed, and each differing
copy is preserved as a pending entry with a new ID and the title marker
`[Recovered duplicate ID <id>]`. A repair failure names the ID and paths and prevents the triggering
mutation; pending copies already written remain available for a later retry.

## Batch Commits

Pending entries are intentionally left uncommitted. After curation or review, call the dedicated MCP operation:

```text
owlbear-memory/commit_memory_batch(session_type="curation")
owlbear-memory/commit_memory_batch(session_type="review")
```

The operation holds the shared writer lock from snapshot validation through `git commit`. It
strictly validates each memory file and tracked deletion, stages only validated non-pending entries
and permitted deletions, then rechecks working-tree bytes and staged blobs. After Git completes, it
compares the committed path set and blobs with the validated snapshot. Unrelated staged paths are
not committed; a staged memory blob that differs from both `HEAD` and the validated file is rejected
without resetting that index entry.

A tracked duplicate-copy deletion is permitted when another file with that ID survives. If the
survivor is not pending, the removal commits with the survivor. If the survivor is pending, the
removal is left unstaged and deferred; the result exposes its path in `deferred_deletions`, and the
CLI prints `note: deferred duplicate deletions: ...`. Curate the survivor before retrying the batch.
Other reviewed entries must first be soft-deleted and committed as tombstones, then purged. Restore
guidance remains in the validation error for a disallowed deletion.

Initial validation and pre-commit recheck failures return tool errors before a commit is created.
Once staging begins, recheck, Git, or hook failures may leave memory paths staged; the operation
does not restore the index, so inspect `git status` and the staged diff before retrying. A
post-commit verification error can occur after `HEAD` has moved; it reports unvalidated changes and
does not reset Git state, so inspect `git show --stat HEAD` as well. Git and hook failures start
with `memory batch commit failed`
and include the failed command, exit status, and bounded captured `stderr` (or `stdout` when
`stderr` is empty). Output is limited to the final 4,096 characters and marked as diagnostic text.
The operation returns the commit SHA or a no-op result when there is nothing to commit. The lower-
level `git.py` module remains an internal implementation detail.

The command-line entry point uses the same bounded diagnostic formatter.

## Dependencies

| Package | Purpose |
| --- | --- |
| `mcp` | MCPServer framework |
| `owlbear-memory` | Shared memory engine, models, and error types (workspace package) |
| `pydantic` | Model validation at the MCP tool layer |
