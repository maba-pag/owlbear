---
name: w-mem-curation
description: "Workflow: Memory curation — deduplicate, consolidate, and prune lessons-learned entries"
user-invocable: false
---

# Memory Curation

Maintain institutional memory by deduplicating, consolidating, and pruning lessons learned from agent task notes. Process inbox entries and promote high-signal findings to project knowledge.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

If dispatched with a curation task ID, claim the task via `start_work` (atomic claim + retrieves task body). Check for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

If dispatched periodically by the orchestrator (no task ID), proceed without claiming.

## Step 1 — Gather Pending Entries

Gather from both active sources (during migration, both are active):

1. **Primary (MCP):** Call `list_entries(status=pending)` to fetch all pending entries from the `owlbearMemory` MCP database. See `h-mcp-memory` for full parameter reference.
2. **Secondary (file-based):** List the repo memory inbox: `memory view /memories/repo/inbox/` — read each file.
3. Scan parent directory: `memory view /memories/repo/` — check for misplaced entries that agents wrote to `/memories/repo/` instead of the inbox. Move any unreviewed entries to the inbox first.
4. Also check task bodies via `show_task` for inline agent notes not written to either source (legacy pattern).
5. Filter to the scope specified (all, last N tasks, tag filter).
6. Collect all entries from both sources for the remaining steps.

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
| CONFLICT (contradicts existing rule) | Create decision request via scribe — do NOT auto-resolve |
| UNCERTAIN (needs user opinion) | Create decision request via scribe — do NOT keep for next cycle |

For HIGH findings: identify which file to change (instruction, skill, or agent) and propose the specific edit. Write the proposal to the curation report.

For CONFLICT/UNCERTAIN findings: use the scribe to check/create a decision request. Present conflicting entries with confidence scores and recommended disposition.

**Deletions:**

- **MCP entries:** `mark_for-deletion(entry_id)` — soft-delete, preserves the entry for auditing.
- **File-based inbox entries:** `memory delete /memories/repo/inbox/{filename}`

**Cross-pollination:** For HIGH findings that benefit agents other than the original author, call `record_learning` with:

- `agent_id`: `curator:cross-pollinate:{original_entry_id}` (lineage tracking)
- `scope_agent`: the target agent(s) that would benefit
- `category`: carry forward the original entry's category unchanged
- `confidence`: carry forward the original entry's confidence, floored at 0.7

Cross-pollinated entries re-enter the pending queue and are evaluated in the next curation cycle.

## Step 5 — Deliverables

### 5a — Write curation-report.json

Write a machine-readable report to `store/memory/curation-report.json` (overwrite each cycle — latest report only).

Format: top-level JSON array, one object per processed entry:

```json
[
  {
    "entry_id": "<MCP entry ID or inbox filename>",
    "content_preview": "<first ~80 chars of entry content>",
    "recommendation": "approve | keep | reject",
    "reason": "<one-line human-readable rationale>"
  }
]
```

This file is consumed by `approve.py _load_curation_report()` to annotate the interactive approval UI with curator recommendations. Include every entry processed in this cycle (HIGH/MEDIUM = `approve`, LOW/NOISE = `reject`, MEDIUM held for next cycle = `keep`).

Write this file **before** appending to the task body.

### 5b — Append to task body

If dispatched with a task ID, include the curation report in your `end_work` note.

## Step 6 — Advance

If dispatched with a task ID, advance via `end_work` (advances status + releases claim).

Return Channel A signal per `r-pipeline-protocol`.

## Output Template

Append to task body (if applicable):

```
## Curation
### Summary
- Entries processed: {N}
- Duplicates found: {dedup_count}
- Promoted (HIGH): {N}
- Kept (MEDIUM): {N}
- Pruned (LOW/NOISE): {N}
- Conflicts flagged: {N}

### Promotions
| Finding | Target File | Proposed Change |
|---------|------------|-----------------|
| {finding} | {file} | {change description} |

### Conflicts
| Finding | Contradicts | Disposition |
|---------|-------------|-------------|
| {finding} | {existing rule} | DR created / kept for review |

### Deletions
| Source | ID/File | Rating | Reason |
|--------|---------|--------|--------|
| {MCP/inbox} | {entry_id or filename} | {NOISE/LOW} | {why} |
```

## Verification Checklist

- [ ] Processed all entries in scope
- [ ] Deduplicated by meaning, not just exact text match
- [ ] Promotions are genuinely actionable + non-obvious + recurring
- [ ] Noise removals are truly generic/empty (not just unfamiliar)
- [ ] Conflicts flagged via scribe, not auto-resolved
- [ ] Report statistics match actions taken
- [ ] Did not fabricate any findings

## Known Pitfalls

- **Auto-resolving conflicts:** Conflicting lessons must go to a decision request. The curator does not have authority to pick a winner when existing rules disagree.
- **Aggressive pruning:** Unfamiliar findings may be non-obvious signals from a different agent context. Only prune if genuinely low-signal.
- **Misplaced inbox entries:** Agents sometimes write to `/memories/repo/` instead of `/memories/repo/inbox/`. Scan the parent directory first.
- **Dedup by exact match only:** Semantic deduplication is needed. "Always use --cov" and "Coverage requires bare --cov flag" are duplicates.
