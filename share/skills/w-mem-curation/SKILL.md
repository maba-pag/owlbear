---
name: w-mem-curation
description: "Workflow: Memory curation — review, scope, deduplicate, and prune MCP memory entries"
user-invocable: false
---

# Memory Curation

> **Audience:** The `memory-curator` agent (periodic or manual dispatch). **When:** Orchestrator dispatches a curation cycle, or the user invokes manually for conflict resolution. **Why:** Turns raw `pending` agent reflections into scoped, quality-checked MCP entries that `recall_memory` surfaces.

Maintain institutional memory by turning raw agent learnings into scoped MCP memory entries. MCP memory is the canonical reviewed store; file-based inbox notes are fallback/migration input only.

## Architecture

The canonical path is:

```text
save_memory -> list_memories/read_memory -> curate_memory(scope_agents=[...]) -> recall_memory
```

Curated and approved MCP entries are what future agents recall. Pending entries are unreviewed and invisible to recall. File-based `/memories/repo/inbox/` entries may still appear during migration or tool outages; valuable file notes are migrated into MCP, then the file note is removed or deferred.

## State Machine

| From | To | Trigger | Tool | Actor |
|------|----|---------|------|-------|
| `pending` | `curated` | Curator validates content and assigns scope | `curate_memory(scope_agents=[...])` | curator agent |
| `curated` | `approved` | User signs off in review prompt | `approve_memory` | human user |
| `approved` | `curated` | Curator edits obsolete or imprecise content | `curate_memory(...)` | curator agent |
| `pending` | removed | Noise/duplicate pruned before commit | `delete_memory` | curator agent |
| `curated` / `approved` | `deleted` | Superseded or invalidated guidance retired | `delete_memory` | curator agent |

The curator does not approve entries. Approval is a user decision through the memory review prompt.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

**Mode detection:**

- **Periodic mode** — dispatched by the orchestrator. Handle clear-cut entries only. Do not call `askQuestions`; defer conflicts and uncertain scope decisions.
- **Manual mode** — invoked directly by the user. Resolve conflicts and uncertain scope through `askQuestions`.

**Deferred queue:** list `/memories/repo/deferred/` and keep `deferred_count` for the return summary.

## Step 1 — Gather Candidates

1. Call `list_memories(states=["pending", "curated", "approved"])`.
2. Read each pending candidate with `read_memory(entry_id=...)`.
3. Keep curated/approved metadata nearby for duplicate and conflict checks. Read likely overlaps before deciding.
4. Inspect `/memories/repo/inbox/` for fallback notes. Treat these as migration candidates, not canonical memory.
5. Scan `/memories/repo/` for misplaced unreviewed notes. Move or process them as inbox candidates.

## Step 2 — Classify Signal

For each MCP pending entry or file-inbox note, classify by meaning:

| Rating | Meaning | Default action |
|--------|---------|----------------|
| PROMOTE | Specific, actionable, non-obvious, and not already covered | Curate into MCP with explicit scope |
| DEFER | Plausible but lacks enough evidence, scope clarity, or wording quality | Leave pending or write deferred note |
| DELETE | Generic, empty, obvious, stale, or wrong | Delete/prune |
| DUPLICATE | Existing curated/approved MCP entry already covers it | Delete pending/file note |
| CONFLICT | Contradicts existing curated/approved memory or project rules | Defer or resolve manually |

Deduplicate by meaning, not wording. Before deleting as duplicate, read the likely existing MCP entry unless metadata alone is conclusive.

## Step 3 — Assign Scope

Every promoted entry needs non-empty `scope_agents`.

| Scope | Use when |
|-------|----------|
| `['builder']`, `['reviewer']`, etc. | The learning applies to one or a few roles |
| `['builder', 'reviewer']` | A shared handoff or quality pattern spans roles |
| `['*']` | The learning applies to nearly every agent |

Prefer targeted scopes. Use `['*']` only for broadly reusable process/tool guidance. Never promote with an empty scope.

## Step 4 — Act On MCP Entries

| Rating | MCP action |
|--------|------------|
| PROMOTE | Call `curate_memory(entry_id=..., scope_agents=[...])`; optionally improve title/content/categories/confidence in the same call |
| DEFER | Leave pending and, in periodic mode, write a deferred note explaining what is unclear |
| DELETE / DUPLICATE | Call `delete_memory(entry_id=...)` |
| CONFLICT | Periodic: write deferred note. Manual: ask the user, then curate/delete according to the decision |

When editing an approved entry, remember `curate_memory` downgrades it to curated. That is intentional; the user must re-approve later.

## Step 5 — Migrate File-Inbox Notes

For each valuable file-based note:

1. Convert only the durable insight into a focused MCP entry with `save_memory(...)` and `source_agent="memory-curator:file-inbox"`.
2. Immediately call `curate_memory(...)` with explicit `scope_agents` when the scope is clear.
3. Delete the file-inbox note after successful MCP curation.
4. If the note is uncertain or conflicting, write a deferred note and leave the original file until resolved.

Do not merge new learnings into thematic `/memories/repo/*.md` files as the promotion path. Existing thematic files are legacy references during migration.

## Step 6 — Batch Commit MCP Memory

Before returning, commit reviewed MCP memory mutations with the state-aware helper:

```bash
uv --project ../owlbear run python -m owlbear_mcp_memory.git curation
```

The `--project` path must point to the OwlBear installation root. Find the correct value from the `ob-memory` server entry in `.vscode/mcp.json` (look for the `--project` argument in the `args` array). The helper stages only non-pending `.owlbear/memory/*.md` entries; do not broad-add `.owlbear/memory`.

## Step 7 — Return Channel A Signal

Return per `r-pipeline-protocol`:

- Periodic mode: `DONE | {P} promoted, {D} pruned` (add `— {K} deferred` when `deferred_count > 0`; add `— {M} migrated` when file notes were moved into MCP)
- Manual mode: concise summary of promoted, pruned, migrated, deferred, and resolved entries

## Verification Checklist

- [ ] Every promoted MCP entry has non-empty `scope_agents`
- [ ] Duplicate checks compared against existing curated/approved MCP entries
- [ ] Noise removals are truly low-signal, not merely unfamiliar
- [ ] Conflicts were deferred in periodic mode or resolved with user input in manual mode
- [ ] File-inbox notes were migrated into MCP before deletion
- [ ] No broad `git add .owlbear/memory` command was used
- [ ] Did not call `approve_memory`

## Known Pitfalls

- **Promoting to thematic files:** legacy thematic files are not the canonical store. Promotion means MCP curation.
- **Global scope by habit:** `['*']` floods all agents. Prefer named role scopes unless the learning is truly universal.
- **Deleting before migration:** file-inbox notes are fallback input. Save and curate the durable insight before removing the file.
- **Auto-resolving conflicts:** conflicting lessons must be deferred in periodic mode or resolved with the user in manual mode.
- **Broad memory commits:** use the state-aware helper so pending entries stay uncommitted.
