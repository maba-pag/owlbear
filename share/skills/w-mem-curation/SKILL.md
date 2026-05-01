---
name: w-mem-curation
description: "Workflow: Memory curation — deduplicate, consolidate, and prune lessons-learned entries"
user-invocable: false
---

# Memory Curation

Maintain institutional memory by deduplicating, consolidating, and pruning lessons learned from agent task notes. Process inbox entries and promote high-signal findings to project knowledge.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

**Mode detection:**

- **Periodic mode** — dispatched by the orchestrator. Handle clear-cut entries only. Do NOT call `askQuestions` or block on user input — the orchestrator pipeline stalls if you do. Write CONFLICT/UNCERTAIN entries to the deferred folder (Step 4).
- **Manual mode** — invoked directly by the user via prompt. Full interactive capabilities: `askQuestions` available. Process both new entries and any items in the deferred folder.

**Deferred folder:** List `/memories/repo/deferred/`. Count files as `deferred_count`. This count appears in the Channel A return (periodic) and determines whether Step 4 processes deferred items (manual).

## Step 1 — Gather Pending Entries

Gather from both active sources (during migration, both are active):

1. **Primary (MCP):** Call `list_entries(status=pending)` to fetch all pending entries from the `owlbearMemory` MCP database. See `h-mcp-memory` for full parameter reference.
2. **Secondary (file-based):** List the repo memory inbox: `memory view /memories/repo/inbox/` — read each file.
3. Scan parent directory: `memory view /memories/repo/` — check for misplaced entries that agents wrote to `/memories/repo/` instead of the inbox. Move any unreviewed entries to the inbox first.
4. Collect all entries from both sources for the remaining steps.

## Step 2 — Deduplicate

Group findings by semantic similarity:

1. Identify near-duplicates (same core insight, different wording).
2. For each group, pick the best-worded version as canonical.
3. Merge supporting evidence from duplicates into the canonical entry.
4. Mark duplicates for removal.
5. Track: `dedup_count`.

## Step 3 — Assess Signal

For each unique finding, evaluate:

1. **Actionable?** — Can an agent use this for better decisions? "Tests should be good" = low signal. "Mock pydantic-settings with `MagicMock(spec=...)` and set every field" = high signal.
2. **Non-obvious?** — Would a competent developer already know this? "Use type hints" = obvious. "Coverage.py MRO crash with dotted module names" = non-obvious.
3. **Recurring?** — Has this come up more than once? Recurring = stronger signal.
4. **Contradicts existing?** — Conflicts with a reviewed lesson?

Rate each: **HIGH** / **MEDIUM** / **LOW** / **NOISE** / **CONFLICT**

## Step 4 — Act

| Rating | Action |
|--------|--------|
| HIGH (recurring, actionable, non-obvious) | Propose changes to instructions, skills, or agent files; **cross-pollinate** if other agents benefit |
| MEDIUM (actionable, single occurrence) | Keep in inbox for next curation cycle |
| LOW (vaguely useful, not actionable) | Mark for deletion |
| NOISE (obvious, generic, empty) | Mark for deletion |
| CONFLICT (contradicts existing rule) | **Periodic:** write to deferred folder. **Manual:** resolve interactively via `askQuestions` |
| UNCERTAIN (needs user opinion) | **Periodic:** write to deferred folder. **Manual:** resolve interactively via `askQuestions` |

For HIGH findings: identify which file to change (instruction, skill, or agent) and propose the specific edit.

**CONFLICT/UNCERTAIN handling by mode:**

- **Periodic mode:** Create a file at `/memories/repo/deferred/{source}-{entry-id}.md` with:
  - The new entry's content
  - The existing rule it contradicts (with file path + line reference)
  - Recommended options (keep new, keep existing, revise existing) with confidence scores

  Do NOT auto-resolve. Do NOT call `askQuestions`.
- **Manual mode:** For each file in `/memories/repo/deferred/`:
  1. Read the file.
  2. Present the conflict to the user via `askQuestions` with the options and confidence scores from the file.
  3. Apply the user's decision (promote the new entry, prune it, or revise the existing rule).
  4. Delete the deferred file after resolution.

**Deletions:**

- **MCP entries:** `mark_for-deletion(entry_id)` — soft-delete, preserves the entry for auditing.
- **File-based inbox entries:** `memory delete /memories/repo/inbox/{filename}`

**Cross-pollination:** For HIGH findings that benefit agents other than the original author, call `record_learning` with:

- `agent_id`: `curator:cross-pollinate:{original_entry_id}` (lineage tracking)
- `scope_agent`: the target agent(s) that would benefit
- `category`: carry forward the original entry's category unchanged
- `confidence`: carry forward the original entry's confidence, floored at 0.7

Cross-pollinated entries re-enter the pending queue and are evaluated in the next curation cycle.

## Step 5 — Return Channel A signal

Return per `r-pipeline-protocol`:

- Periodic mode: `DONE | {N} promoted, {M} pruned` (add `— {K} items need manual curation` when `deferred_count > 0`)
- Manual mode: summary of actions taken (promotions, resolutions, deletions)

## Step 6 — Done

Curation actions are the deliverable.

## Verification Checklist

- [ ] Processed all entries in scope
- [ ] Deduplicated by meaning, not just exact text match
- [ ] Promotions are genuinely actionable + non-obvious + recurring
- [ ] Noise removals are truly generic/empty (not just unfamiliar)
- [ ] Conflicts deferred to `/memories/repo/deferred/` (periodic) or resolved via user input (manual)
- [ ] Did not fabricate any findings

## Known Pitfalls

- **Auto-resolving conflicts:** Conflicting lessons must be deferred to `/memories/repo/deferred/` in periodic mode for manual resolution. The curator does not have authority to pick a winner when existing rules disagree.
- **Aggressive pruning:** Unfamiliar findings may be non-obvious signals from a different agent context. Only prune if genuinely low-signal.
- **Misplaced inbox entries:** Agents sometimes write to `/memories/repo/` instead of `/memories/repo/inbox/`. Scan the parent directory first.
- **Dedup by exact match only:** Semantic deduplication is needed. "Always use --cov" and "Coverage requires bare --cov flag" are duplicates.
