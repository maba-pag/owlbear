---
name: w-mem-curation
description: "Workflow: Memory curation — deduplicate, consolidate, and prune lessons-learned entries"
user-invocable: false
---

# Memory Curation

Maintain institutional memory by deduplicating, consolidating, and pruning lessons learned from agent task notes. Process inbox entries and merge high-signal findings into the existing thematic knowledge files.

## Architecture

Repo memory (`/memories/repo/`) is organized as **thematic files** — each file answers a specific question an agent would have in a specific role/context. Examples: `reviewer-proof-quality.md`, `builder-pitfalls.md`, `engine-review-patterns.md`.

**The cardinal rule:** promotion means **merge into the right thematic file**, not create a new standalone file. If no existing file fits, create a new thematic file with a descriptive name — but this should be rare.

**Inbox** (`/memories/repo/inbox/`) holds raw agent field notes awaiting triage. **Deferred** (`/memories/repo/deferred/`) holds conflicts needing manual resolution.

## State Machine

Memory lifecycle transitions are explicit and tool-driven:

| From | To | Trigger | Tool | Actor |
|------|----|---------|------|-------|
| `pending` | `curated` | Curator promotes after review | `curate_memory(scope_agents=[...])` | curator agent |
| `curated` | `approved` | User signs off | `approve_memory` | human user |
| `approved` | `curated` | Any curator edit (auto-downgrade) | `curate_memory(...)` | curator agent |
| `pending` | `deleted` | Noise/duplicate pruned | `delete_memory` (hard delete) | curator agent |
| `curated` | `deleted` | Superseded or invalidated | `delete_memory` (soft delete) | curator agent |
| `approved` | `deleted` | Obsolete knowledge purged | `delete_memory` (soft delete) | curator agent |

Purge flow: periodic curation may mark previously approved entries as `deleted` when they become obsolete, stale, or replaced by better guidance.

Tool hints are part of the workflow signal:

- `curate_memory` returns hints describing promotion/downgrade/update path.
- `delete_memory` returns whether hard-delete (pending) or soft-delete (curated/approved) was applied.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

**Mode detection:**

- **Periodic mode** — dispatched by the orchestrator. Handle clear-cut entries only. Do NOT call `askQuestions` or block on user input — the orchestrator pipeline stalls if you do. Write CONFLICT/UNCERTAIN entries to the deferred folder (Step 4).
- **Manual mode** — invoked directly by the user via prompt. Full interactive capabilities: `askQuestions` available. Process both new entries and any items in the deferred folder.

**Deferred folder:** List `/memories/repo/deferred/`. Count files as `deferred_count`. This count appears in the Channel A return (periodic) and determines whether Step 4 processes deferred items (manual).

## Step 1 — Gather and Inventory

1. **Inventory existing thematic files:** `memory view /memories/repo/` — list all files (excluding `inbox/`, `deferred/`). These are the merge targets. Read each file's heading to understand its scope.
2. **Capacity check:** count standalone files (not thematic). If any exist, add them to the consolidation queue (Step 4b).
3. **Primary (MCP):** Call `list_memories(states=["pending"])` to fetch pending entries from the `owlbearMemory` MCP database. See `h-mcp-memory` for full parameter reference.
4. For each candidate ID, call `read_memory(entry_id=...)` to inspect the full entry content before scoring.
5. **Secondary (file-based):** List the repo memory inbox: `memory view /memories/repo/inbox/` — read each file.
6. Scan parent directory for misplaced entries agents wrote to `/memories/repo/` instead of the inbox. Move any unreviewed entries to the inbox first.
7. Collect all entries from both sources for the remaining steps.

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
4. **Already covered?** — Read the target thematic file. If the insight is already there (even in different words), this is a duplicate, not a promotion.
5. **Contradicts existing?** — Conflicts with a reviewed lesson?

Rate each: **HIGH** / **MEDIUM** / **LOW** / **NOISE** / **DUPLICATE** / **CONFLICT**

## Step 4 — Act

| Rating | Action |
|--------|--------|
| HIGH (recurring, actionable, non-obvious, not already covered) | **Merge into the matching thematic file** (see Promotion below) |
| MEDIUM (actionable, single occurrence) | Keep in inbox for next curation cycle |
| LOW (vaguely useful, not actionable) | Delete |
| NOISE (obvious, generic, empty) | Delete |
| DUPLICATE (already in thematic file) | Delete |
| CONFLICT (contradicts existing rule) | **Periodic:** write to deferred folder. **Manual:** resolve interactively via `askQuestions` |
| UNCERTAIN (needs user opinion) | **Periodic:** write to deferred folder. **Manual:** resolve interactively via `askQuestions` |

### Promotion = Merge

**Never create a new standalone `review-*.md` file.** Instead:

1. Identify which thematic file the finding belongs to by matching the agent role and decision context.
2. Read the target thematic file.
3. Find the right section within the file (or add a new section heading if needed).
4. Append the finding as a bullet under that section, matching the file's existing style.
5. If no thematic file fits AND the finding represents a genuinely new category, create a new thematic file with a descriptive name following the pattern `{role}-{context}.md` (e.g., `reviewer-proof-quality.md`, `builder-pitfalls.md`).

### CONFLICT/UNCERTAIN handling by mode

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

### Deletions

- **MCP entries:** `delete_memory(entry_id)` — pending entries are hard-deleted; curated/approved entries are soft-deleted to `state=deleted`.
- **File-based inbox entries:** `memory delete /memories/repo/inbox/{filename}`

## Step 4b — Consolidation (capacity-triggered)

If Step 1 found standalone files (not matching the `{role}-{context}.md` thematic pattern), consolidate them:

1. Read each standalone file.
2. Identify which thematic file it belongs to.
3. Merge its content into the thematic file (following Promotion rules above).
4. Delete the standalone file.
5. Track: `consolidated_count`.

In periodic mode, consolidate up to 10 files per cycle to bound execution time. Flag remaining for next cycle.

## Step 5 — Return Channel A signal

Return per `r-pipeline-protocol`:

- Periodic mode: `DONE | {N} merged, {M} pruned` (add `— {K} items need manual curation` when `deferred_count > 0`; add `— {C} consolidated` when `consolidated_count > 0`)
- Manual mode: summary of actions taken (merges, resolutions, deletions, consolidations)

## Step 6 — Done

Curation actions are the deliverable.

## Verification Checklist

- [ ] Processed all entries in scope
- [ ] Deduplicated by meaning, not just exact text match
- [ ] Promotions merged into existing thematic files (no new standalone files created)
- [ ] Noise removals are truly generic/empty (not just unfamiliar)
- [ ] Conflicts deferred to `/memories/repo/deferred/` (periodic) or resolved via user input (manual)
- [ ] Did not fabricate any findings
- [ ] Checked target thematic file for existing coverage before merging

## Known Pitfalls

- **Creating standalone files instead of merging:** The #1 anti-pattern. Every promotion should append to an existing thematic file. New thematic files are only justified for genuinely new categories.
- **Auto-resolving conflicts:** Conflicting lessons must be deferred to `/memories/repo/deferred/` in periodic mode for manual resolution.
- **Aggressive pruning:** Unfamiliar findings may be non-obvious signals from a different agent context. Only prune if genuinely low-signal.
- **Misplaced inbox entries:** Agents sometimes write to `/memories/repo/` instead of `/memories/repo/inbox/`. Scan the parent directory first.
- **Dedup by exact match only:** Semantic deduplication is needed. "ruff caught an unused import" and "linter flagged unused import" are the same finding.
- **Already-covered findings:** Before promoting, read the target thematic file. If the insight is already captured, delete the inbox entry as a duplicate.
