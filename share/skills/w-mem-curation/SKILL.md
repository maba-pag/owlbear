---
name: w-mem-curation
description: "Workflow: Memory curation — review, scope, deduplicate, and prune MCP memory entries"
user-invocable: false
---

# Memory Curation

> **Audience:** The `memory-curator` agent (automatic or interactive mode). **When:** An automatic run (`Curate: automatic`, from Delivery or a chat) or the owner curating with the agent in a chat. **Why:** Turns raw `pending` agent reflections into scoped, quality-checked MCP entries that `recall_memory` surfaces.

Maintain institutional memory by turning raw agent learnings into scoped MCP memory entries. MCP memory is the canonical reviewed store; the retired VS Code `/memories/` store is not an inbox or fallback.

## Architecture

The canonical path is:

```text
save_memory -> list_memories/read_memory -> curate_memory(entry_id=..., revision=..., scope_agents=[...]) -> recall_memory
                                          \-> make_global(entry_id=..., revision=...) for a lesson that holds in any project
```

Curated and approved MCP entries are what future agents recall. Pending entries are unreviewed and invisible to recall. Memory curation operates on MCP entries only.

## Revision-bound mutations

`approve_memory`, `curate_memory`, and `delete_memory` require the current `revision` returned by
`read_memory` or `list_memories`. This 16-character lowercase hex token covers `title`, `content`,
`categories`, `confidence`, and `scope_agents`, not `state`, assessment counters, or timestamps. A
stale revision is refused with an error naming the expected and current revisions and instructing
the caller to re-read before retrying. Re-read the entry and retry with the new revision.

## State Machine

| From | To | Trigger | Tool | Actor |
| --- | --- | --- | --- | --- |
| `pending` | `curated` | Curator validates content and assigns scope | `curate_memory(entry_id=..., revision=..., scope_agents=[...])` | curator agent |
| `curated` | `approved` | User signs off in review prompt | `approve_memory(entry_id=..., revision=...)` | human user |
| `approved` | `curated` | Curator edits obsolete or imprecise content | `curate_memory(entry_id=..., revision=...)` | curator agent |
| `curated` / `approved` | `contested` | First factually-wrong assessment | `assess_memories` | builder |
| `contested` | `disputed` | A second task reports the entry factually wrong | `assess_memories` | builder |
| `curated` / `approved` / `contested` | `stale` | Non-use exceeds the slot-efficiency threshold | `assess_memories` | memory service |
| `contested` / `disputed` / `stale` | `approved` | User resolves the exceptional state | Memory page | human user |
| `pending` | removed | Noise/duplicate pruned before commit | `delete_memory(entry_id=..., revision=...)` | curator agent |
| `curated` / `approved` / `contested` / `disputed` / `stale` | `deleted` | Superseded or invalidated guidance retired | `delete_memory(entry_id=..., revision=...)` | curator agent |

The curator does not approve entries. Approval is a user decision through the memory review prompt.
The curator also does not resolve exceptional states. `curate_memory` is blocked for `contested`,
`disputed`, and `stale`; the user resolves them on the Delivery engine's Memory page.

## Step 0 — Setup

Before curation, invoke directly callable Memory operations as granted; a deferred inventory listing
does not override those bindings. For each required Memory operation without a direct callable
binding (`list_memories`, `read_memory`, `curate_memory`, `delete_memory`, `make_global`,
`curation_threshold`, `delete_agent_memories`, `rename_agent_memories`, `commit_memory_batch`), run one
`tool_search` whose query is exactly that operation name.

Require callable bindings for `list_memories`, `curation_threshold` and `commit_memory_batch` before any
candidate read or mutation. If either required binding is unavailable or its search returns a tool error,
report the exact missing operation and return without changing MCP memory or the workspace. The
remaining bindings are required before using their corresponding operations; do not substitute a
different memory store or direct Git command.

**Mode detection:**

- **Automatic mode** — the request is `Curate: automatic`. Nobody answers: never call `askQuestions`.
- **Interactive mode** — any other request; the owner is in the chat and answers through `askQuestions`.

**Threshold:** call `curation_threshold()` once; its `threshold`, set on the Settings page, is the confidence at
or above which you act alone (TD-400). Unset (`null`), act on nothing alone: ask the owner in interactive mode, and in
automatic mode report every entry as skipped with the tool's `error`.

**Folders:** without a `folder`, the tools work on this server's own project folder. When the request names other
project folders of the shared repository (or `all`), pass `folder=<name>` to `list_memories`, `read_memory`,
`curate_memory`, `delete_memory`, `make_global` and `commit_memory_batch`, one folder at a time. Global memory is
never a `folder`; it changes only by `make_global`.

Classify content before provenance or scope. Delete low-value content regardless of identity. For
keep-worthy unfamiliar named provenance, require another reviewed non-pending entry or a readable
local definition; candidate text cannot self-prove identity. `*` is anonymous provenance and needs
no source corroboration, but it does not waive separate target-scope evidence. Identity-only
uncertainty remains pending and is omitted from automatic skip and conflict summaries. Conflicts and
ordinary content or scope uncertainty remain reportable.

## Confidence and the threshold

For each entry, decide everything you would do to it (keep, edit, scope, merge, delete, make global) and state one
confidence, 0 to 100, that this whole set is right. Then:

| Confidence | Automatic mode | Interactive mode |
| --- | --- | --- |
| At or above the threshold | Act alone, `make_global` included | Act alone, `make_global` included |
| Below the threshold | Leave the entry as it is; report it as skipped with the reason | Ask the owner, one entry per question, your proposed set as the recommendation |

- A conflict with curated or approved memory or with project rules lowers your confidence; resolve it alone only
  when your confidence in the whole set is still at or above the threshold, and report which side stands and why.
- `make_global` is for a lesson that holds in any project; the saver's `recommended` scope is evidence, not a
  decision. `list_memories` and `read_memory` mark each entry's `where`: one in `global` is in Global memory
  already, evidence beside the folder, never moved again. In interactive mode, propose Make global for such a lesson whenever you do not make it global alone.
- An automatic run never changes an entry it skips. Which runs start is the scheduler's: idle time passes over an
  unchanged skipped entry, while the button and a merge judge it again.

## Step 1 — Gather Candidates

1. Call `list_memories(states=["pending", "curated", "approved", "contested", "disputed", "stale"])`.
2. Read each pending candidate with `read_memory(entry_id=...)`.
3. Keep curated/approved metadata nearby for duplicate and conflict checks. Treat exceptional-state
 metadata as unavailable for curation until the user resolves it on the Memory page. Read likely overlaps
 before deciding.

## Step 2 — Classify Signal

For each MCP pending entry, classify by meaning:

| Rating | Meaning | Default action |
| --- | --- | --- |
| PROMOTE | Specific, actionable, non-obvious, and not already covered | Curate into MCP with explicit scope |
| GLOBAL | PROMOTE-worthy and holds in any project, not only this one | Curate, then `make_global` |
| DEFER | Plausible but lacks enough evidence, scope clarity, or wording quality | Leave pending and report the entry ID |
| DELETE | Generic, empty, obvious, stale, or wrong | Delete/prune |
| DUPLICATE | Existing curated/approved MCP entry already covers it | Delete pending/file note |
| CONFLICT | Contradicts existing curated/approved memory or project rules | Resolve it at or above the threshold; below it, skip (automatic) or ask the owner (interactive) |

Deduplicate by meaning, not wording. Before deleting as duplicate, read the likely existing MCP entry unless metadata alone is conclusive.

## Step 3 — Assign Scope

Every promoted entry needs non-empty `scope_agents`.

| Scope | Use when |
| --- | --- |
| `['builder']`, `['reviewer']`, etc. | The learning applies to one or a few roles |
| `['builder', 'reviewer']` | A shared handoff or quality pattern spans roles |
| `['*']` | The learning applies to nearly every agent |

Prefer targeted scopes. Use `['*']` only for broadly reusable process/tool guidance. Never promote with an empty scope.
Named scope requires another reviewed non-pending memory, a readable local `.agent.md`, or explicit
user confirmation; candidate text cannot corroborate its own named identity or scope. When an agent
is renamed or deleted, use `rename_agent_memories` or `delete_agent_memories`; never retain an alias
in relevance scope. A deleted agent may remain in immutable historical provenance.

## Step 4 — Act On MCP Entries

| Rating | MCP action |
| --- | --- |
| PROMOTE | Call `curate_memory(entry_id=..., revision=entry["revision"], scope_agents=[...])`; optionally improve title/content/categories/confidence in the same call |
| GLOBAL | Curate it first if pending, then call `make_global(entry_id=..., revision=...)` with the revision after curation |
| DEFER | Leave pending; in automatic mode report ordinary content/scope uncertainty or a conflict as skipped; do not report identity-only uncertainty |
| DELETE / DUPLICATE | Call `delete_memory(entry_id=..., revision=entry["revision"])` |
| CONFLICT | At or above the threshold: curate/delete and report the resolution. Below it, automatic: leave pending and report it as skipped; interactive: ask the owner, then act on the answer |

Any action below the threshold follows the table in "Confidence and the threshold" first.

When editing an approved entry, remember `curate_memory` downgrades it to curated. That is intentional; the user must re-approve later.

## Step 5 — Retired File Store

Do not inspect, create, migrate, or defer notes in `/memories/` paths. If old file-based memory appears, report it as stale configuration and ask the user before taking destructive action.

## Step 6 — Batch Commit MCP Memory

Before returning, commit reviewed MCP memory mutations with the dedicated MCP operation:

```text
owlbear-memory/commit_memory_batch(session_type="curation")            # this server's own folder
owlbear-memory/commit_memory_batch(session_type="curation", folder=...) # each other folder you changed
```

The MCP operation stages only non-pending entries of the memory store and returns the commit SHA or a no-op result. `make_global` commits its own move. Do not use a terminal or broad-add the memory folder.

## Step 7 — Return Channel A Signal

Return the verdict:

- Automatic mode: `DONE | {P} promoted, {D} pruned, {G} made global` (add `— {K} skipped ({entry IDs})` for
  reportable ordinary uncertainty or conflicts only; exclude identity-only pending entries), then the report as one
  fenced `json` block: `{"threshold": T, "entries": [{"folder": "...", "entry_id": "...", "action": "...",
  "confidence": N, "reason": "..."}]}`, one item per entry you judged, `reason` set for a skip.
- Interactive mode: concise summary of promoted, pruned, made global, asked, and skipped entries, each with its
  confidence

## Verification Checklist

- [ ] Every promoted MCP entry has non-empty `scope_agents`
- [ ] Every named scope has independent corroboration or explicit manual user confirmation
- [ ] Duplicate checks compared against existing curated/approved MCP entries
- [ ] Noise removals are truly low-signal, not merely unfamiliar
- [ ] Each judged entry has one stated confidence; below the threshold nothing changed alone
- [ ] Conflicts below the threshold were skipped (automatic) or asked (interactive); each resolved alone says why
- [ ] No `/memories/` file store was used for curation
- [ ] No broad `git add` of the memory folder was used
- [ ] Did not call `approve_memory`

## Known Pitfalls

- **Using retired file memory:** `/memories/` paths are no longer an agent memory store. Promotion means MCP curation.
- **Global scope by habit:** `['*']` floods all agents. Prefer named role scopes unless the learning is truly universal.
- **Resolving conflicts on a guess:** below the threshold a conflict is skipped (automatic) or asked (interactive); none is resolved silently.
- **Reporting identity-only uncertainty:** keep it pending silently in automatic mode; do not add its count or ID to skip/conflict summaries.
- **Global by habit:** `make_global` only for a lesson that holds in any project, never because the saver recommended it.
- **Broad memory commits:** use `commit_memory_batch` so pending entries stay uncommitted.
- **Manual lifecycle rewrites:** use the agent lifecycle tools when definitions are renamed or
 deleted so provenance and relevance cannot drift.
