---
name: w-mem-curation
description: "Workflow: Memory curation — review, scope, deduplicate, and prune MCP memory entries"
user-invocable: false
---

# Memory Curation

> **Audience:** The `memory-curator` agent (periodic or manual dispatch). **When:** Orchestrator dispatches a curation cycle, or the user invokes manually for conflict resolution. **Why:** Turns raw `pending` agent reflections into scoped, quality-checked MCP entries that `recall_memory` surfaces.

Maintain institutional memory by turning raw agent learnings into scoped MCP memory entries. MCP memory is the canonical reviewed store; the retired VS Code `/memories/` store is not an inbox or fallback.

## Architecture

The canonical path is:

```text
save_memory -> list_memories/read_memory -> curate_memory(scope_agents=[...]) -> recall_memory
```

Curated and approved MCP entries are what future agents recall. Pending entries are unreviewed and invisible to recall. Memory curation operates on MCP entries only.

## State Machine

| From | To | Trigger | Tool | Actor |
| --- | --- | --- | --- | --- |
| `pending` | `curated` | Curator validates content and assigns scope | `curate_memory(scope_agents=[...])` | curator agent |
| `curated` | `approved` | User signs off in review prompt | `approve_memory` | human user |
| `approved` | `curated` | Curator edits obsolete or imprecise content | `curate_memory(...)` | curator agent |
| `curated` / `approved` | `contested` | First factually-wrong assessment | `assess_memories` | task-owning agent |
| `contested` | `disputed` | A second task reports the entry factually wrong | `assess_memories` | task-owning agent |
| `curated` / `approved` / `contested` | `stale` | Non-use exceeds the slot-efficiency threshold | `assess_memories` | memory service |
| `contested` / `disputed` / `stale` | `approved` | User resolves the exceptional state | Cockpit | human user |
| `pending` | removed | Noise/duplicate pruned before commit | `delete_memory` | curator agent |
| `curated` / `approved` / `contested` / `disputed` / `stale` | `deleted` | Superseded or invalidated guidance retired | `delete_memory` | curator agent |

The curator does not approve entries. Approval is a user decision through the memory review prompt.
The curator also does not resolve exceptional states. `curate_memory` is blocked for `contested`,
`disputed`, and `stale`; the user resolves them from Cockpit's `/memories` page.

## Step 0 — Setup

**Mode detection:**

- **Periodic mode** — dispatched by the orchestrator. Handle clear-cut entries only. Do not call `askQuestions`; defer conflicts and ordinary content or scope uncertainty.
- **Manual mode** — invoked directly by the user. Resolve conflicts and uncertain scope through `askQuestions`.

Classify content before provenance or scope. Delete low-value content regardless of identity. For
keep-worthy unfamiliar named provenance, require another reviewed non-pending entry or a readable
local definition; candidate text cannot self-prove identity. `*` is anonymous provenance and needs
no source corroboration, but it does not waive separate target-scope evidence. Identity-only
uncertainty remains pending and is omitted from periodic defer and conflict summaries. Conflicts and
ordinary content or scope uncertainty remain reportable.

## Step 1 — Gather Candidates

1. Call `list_memories(states=["pending", "curated", "approved", "contested", "disputed", "stale"])`.
2. Read each pending candidate with `read_memory(entry_id=...)`.
3. Keep curated/approved metadata nearby for duplicate and conflict checks. Treat exceptional-state
 metadata as unavailable for curation until the user resolves it in Cockpit. Read likely overlaps
 before deciding.

## Step 2 — Classify Signal

For each MCP pending entry or file-inbox note, classify by meaning:

| Rating | Meaning | Default action |
| --- | --- | --- |
| PROMOTE | Specific, actionable, non-obvious, and not already covered | Curate into MCP with explicit scope |
| DEFER | Plausible but lacks enough evidence, scope clarity, or wording quality | Leave pending and report the entry ID |
| DELETE | Generic, empty, obvious, stale, or wrong | Delete/prune |
| DUPLICATE | Existing curated/approved MCP entry already covers it | Delete pending/file note |
| CONFLICT | Contradicts existing curated/approved memory or project rules | Leave pending or resolve manually |

Deduplicate by meaning, not wording. Before deleting as duplicate, read the likely existing MCP entry unless metadata alone is conclusive.

## Step 3 — Assign Scope

Every promoted entry needs non-empty `scope_agents`.

| Scope | Use when |
| --- | --- |
| `['builder']`, `['build-reviewer']`, etc. | The learning applies to one or a few roles |
| `['builder', 'build-reviewer']` | A shared handoff or quality pattern spans roles |
| `['*']` | The learning applies to nearly every agent |

Prefer targeted scopes. Use `['*']` only for broadly reusable process/tool guidance. Never promote with an empty scope.
Named scope requires another reviewed non-pending memory, a readable local `.agent.md`, or explicit
user confirmation; candidate text cannot corroborate its own named identity or scope. When an agent
is renamed or deleted, use `rename_agent_memories` or `delete_agent_memories`; never retain an alias
in relevance scope. A deleted agent may remain in immutable historical provenance.

## Step 4 — Act On MCP Entries

| Rating | MCP action |
| --- | --- |
| PROMOTE | Call `curate_memory(entry_id=..., scope_agents=[...])`; optionally improve title/content/categories/confidence in the same call |
| DEFER | Leave pending and, in periodic mode, include ordinary content/scope uncertainty or conflict in the return report; do not report identity-only uncertainty |
| DELETE / DUPLICATE | Call `delete_memory(entry_id=...)` |
| CONFLICT | Periodic: leave pending and report the conflict. Manual: ask the user, then curate/delete according to the decision |

When editing an approved entry, remember `curate_memory` downgrades it to curated. That is intentional; the user must re-approve later.

## Step 5 — Retired File Store

Do not inspect, create, migrate, or defer notes in `/memories/` paths. If old file-based memory appears, report it as stale configuration and ask the user before taking destructive action.

## Step 6 — Batch Commit MCP Memory

Before returning, commit reviewed MCP memory mutations with the dedicated MCP operation:

```text
owlbear-memory/commit_memory_batch(session_type="curation")
```

The MCP operation stages only non-pending `.owlbear/memory/*.md` entries and returns the commit SHA or a no-op result. Do not use a terminal or broad-add `.owlbear/memory`.

## Step 7 — Return Channel A Signal

Return the verdict:

- Periodic mode: `DONE | {P} promoted, {D} pruned` (add `— {K} pending conflicts/uncertain ({entry IDs})` for reportable ordinary uncertainty or conflicts only; exclude identity-only pending entries)
- Manual mode: concise summary of promoted, pruned, deferred, and resolved entries

## Verification Checklist

- [ ] Every promoted MCP entry has non-empty `scope_agents`
- [ ] Every named scope has independent corroboration or explicit manual user confirmation
- [ ] Duplicate checks compared against existing curated/approved MCP entries
- [ ] Noise removals are truly low-signal, not merely unfamiliar
- [ ] Conflicts were deferred in periodic mode or resolved with user input in manual mode
- [ ] No `/memories/` file store was used for curation
- [ ] No broad `git add .owlbear/memory` command was used
- [ ] Did not call `approve_memory`

## Known Pitfalls

- **Using retired file memory:** `/memories/` paths are no longer an agent memory store. Promotion means MCP curation.
- **Global scope by habit:** `['*']` floods all agents. Prefer named role scopes unless the learning is truly universal.
- **Auto-resolving conflicts:** conflicting lessons must be deferred in periodic mode or resolved with the user in manual mode.
- **Reporting identity-only uncertainty:** keep it pending silently in periodic mode; do not add its count or ID to defer/conflict summaries.
- **Broad memory commits:** use `commit_memory_batch` so pending entries stay uncommitted.
- **Manual lifecycle rewrites:** use the agent lifecycle tools when definitions are renamed or
 deleted so provenance and relevance cannot drift.
