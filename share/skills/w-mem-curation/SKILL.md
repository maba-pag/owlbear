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
|------|----|---------|------|-------|
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

- **Periodic mode** — dispatched by the orchestrator. Handle clear-cut entries only. Do not call `askQuestions`; defer conflicts and uncertain scope decisions.
- **Manual mode** — invoked directly by the user. Resolve conflicts and uncertain scope through `askQuestions`.

Track deferred items by leaving MCP entries pending and recording their entry IDs in the return summary.

## Step 1 — Gather Candidates

1. Call `list_memories(states=["pending", "curated", "approved", "contested", "disputed", "stale"])`.
2. Read each pending candidate with `read_memory(entry_id=...)`.
3. Keep curated/approved metadata nearby for duplicate and conflict checks. Treat exceptional-state
 metadata as unavailable for curation until the user resolves it in Cockpit. Read likely overlaps
 before deciding.

## Step 2 — Classify Signal

For each MCP pending entry or file-inbox note, classify by meaning:

| Rating | Meaning | Default action |
|--------|---------|----------------|
| PROMOTE | Specific, actionable, non-obvious, and not already covered | Curate into MCP with explicit scope |
| DEFER | Plausible but lacks enough evidence, scope clarity, or wording quality | Leave pending and report the entry ID |
| DELETE | Generic, empty, obvious, stale, or wrong | Delete/prune |
| DUPLICATE | Existing curated/approved MCP entry already covers it | Delete pending/file note |
| CONFLICT | Contradicts existing curated/approved memory or project rules | Leave pending or resolve manually |

Deduplicate by meaning, not wording. Before deleting as duplicate, read the likely existing MCP entry unless metadata alone is conclusive.

## Step 3 — Assign Scope

Every promoted entry needs non-empty `scope_agents`.

| Scope | Use when |
|-------|----------|
| `['builder']`, `['build-reviewer']`, etc. | The learning applies to one or a few roles |
| `['builder', 'build-reviewer']` | A shared handoff or quality pattern spans roles |
| `['*']` | The learning applies to nearly every agent |

Prefer targeted scopes. Use `['*']` only for broadly reusable process/tool guidance. Never promote with an empty scope.

## Step 4 — Act On MCP Entries

| Rating | MCP action |
|--------|------------|
| PROMOTE | Call `curate_memory(entry_id=..., scope_agents=[...])`; optionally improve title/content/categories/confidence in the same call |
| DEFER | Leave pending and, in periodic mode, include the entry ID and uncertainty in the return report |
| DELETE / DUPLICATE | Call `delete_memory(entry_id=...)` |
| CONFLICT | Periodic: leave pending and report the conflict. Manual: ask the user, then curate/delete according to the decision |

When editing an approved entry, remember `curate_memory` downgrades it to curated. That is intentional; the user must re-approve later.

## Step 5 — Retired File Store

Do not inspect, create, migrate, or defer notes in `/memories/` paths. If old file-based memory appears, report it as stale configuration and ask the user before taking destructive action.

## Step 6 — Batch Commit MCP Memory

Before returning, commit reviewed MCP memory mutations with the state-aware helper:

```bash
uv --project ../owlbear run python -m owlbear_memory_mcp.git curation
```

The `--project` path must point to the OwlBear installation root. Find the correct value from the `owlbear-memory` server entry in `.vscode/mcp.json` (look for the `--project` argument in the `args` array). The helper stages only non-pending `.owlbear/memory/*.md` entries; do not broad-add `.owlbear/memory`.

## Step 7 — Return Channel A Signal

Return the verdict:

- Periodic mode: `DONE | {P} promoted, {D} pruned` (add `— {K} pending conflicts/uncertain` when unresolved entries remain)
- Manual mode: concise summary of promoted, pruned, deferred, and resolved entries

## Verification Checklist

- [ ] Every promoted MCP entry has non-empty `scope_agents`
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
- **Broad memory commits:** use the state-aware helper so pending entries stay uncommitted.
