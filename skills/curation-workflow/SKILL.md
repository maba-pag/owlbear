---
name: curation-workflow
description: "Knowledge curation workflow: gather recent entries → deduplicate → assess signal → promote/prune/flag → report. Used by the curator agent."
user-invocable: false
---

# Curation Workflow

Step-by-step process for maintaining institutional memory — deduplicating,
consolidating, and pruning lessons learned from agent task notes.

## kanban-md Commands

| Action | Command |
|--------|---------|
| Read task (if dispatched with ID) | `kanban\kanban-md.exe show {id}` |
| Append report (if dispatched with ID) | `kanban\kanban-md.exe edit {id} -a "## Curation\n{content}" -t` |
| Claim + show task (MCP) | `start_work {id}` |
| Append to task body (MCP) | `edit_task {id}` |
| Advance + release (MCP) | `end_work {id}` |

Most curator work uses the memory tool, not kanban-md. These commands are only needed when dispatched with a specific curation task ID. See kanban-md skill for claiming protocol and pitfalls.

## Step 1 — Gather inbox entries

Gather pending lessons from both active sources:

1. **Primary (MCP):** Call `list_entries(status=pending)` to fetch all pending entries from the `owlbearMemory` MCP database.
2. **Migration secondary (file-based):** List the repo memory inbox: `memory view /memories/repo/inbox/` — read each file to gather file-based entries accumulated during the migration period.
3. Scan parent directory: `memory view /memories/repo/` — check for misplaced entries
   that agents wrote directly to `/memories/repo/` instead of the inbox. Move any
   unreviewed entries found there into the inbox before processing.
4. Also check task bodies (`kanban\kanban-md.exe show {id}`) (MCP: `show-task(task_id="{id}")`) for any inline agent notes
   that weren't written to the inbox (legacy pattern)
5. Filter to the scope specified (all, last N tasks, tag filter)
6. Collect all entries from both sources for the remaining steps

## Step 2 — Deduplicate

Group findings by semantic similarity:

1. Identify near-duplicates (same core insight, different wording)
2. For each group, pick the best-worded version as the canonical entry
3. Merge supporting evidence from duplicates into the canonical entry
4. Mark duplicates for removal
5. Track: `dedup_count` (how many duplicates found)

## Step 3 — Assess signal

For each unique finding, evaluate:

1. **Actionable?** — Can an agent actually use this to make a better decision?
   "Tests should be good" = low signal. "Mock pydantic-settings models with `MagicMock(spec=...)` and set every accessed field explicitly" = high signal.
2. **Non-obvious?** — Would a competent developer already know this?
   "Use type hints" = obvious. "Coverage.py MRO crash when using dotted module names with --cov" = non-obvious.
3. **Recurring?** — Has this come up more than once? Recurring findings are stronger signals.
4. **Contradicts existing?** — Does it conflict with a `reviewed` lesson?

Rate each: **HIGH** / **MEDIUM** / **LOW** / **NOISE** / **CONFLICT**

## Step 4 — Act

Based on assessment:

| Rating                                    | Action                                                                                              |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------- |
| HIGH (recurring, actionable, non-obvious) | Propose changes to instructions, skills, or agent files; **CROSS-POLLINATE** if other agents benefit |
| MEDIUM (actionable but single occurrence) | Keep in inbox for next curation cycle                                                               |
| LOW (vaguely useful but not actionable)   | Mark for deletion                                                                                   |
| NOISE (obvious, generic, or empty)        | Mark for deletion                                                                                   |
| CONFLICT (contradicts existing rule)      | Create a **decision request** — do NOT auto-resolve                                                 |
| UNCERTAIN (needs user opinion, not data)  | Create a **decision request** — do NOT keep for next cycle                                          |

For HIGH findings: identify which file to change (instruction, skill, or agent) and
propose the specific edit. Write the proposal to the curation report. After user
approval, make the change and delete the inbox entry.

For CONFLICT / UNCERTAIN findings: use the **scribe** agent to check/create a
decision request. Present the conflicting entries or the uncertain finding as the
concern, include your confidence scores, and the recommended disposition. The scribe
creates the DR with proper frontmatter and blocks the task automatically.

For deletions:

- **MCP entries:** `mark_for_deletion(entry_id)` — soft-delete, preserves the entry for auditing until permanently removed by a reviewer.
- **File-based inbox entries:** `memory delete /memories/repo/inbox/{filename}`

**CROSS-POLLINATE action:** For HIGH findings that benefit agents other than the original author, call `record_learning` with:

- `agent_id`: `curator:cross-pollinate:{original_entry_id}` (lineage tracking, not a filter)
- `scope_agent`: the target agent(s) that would benefit
- `category`: carry forward the original entry's category unchanged (`preference`, `knowledge`, `context`, `behavior`, or `goal`)
- `confidence`: carry forward the original entry's confidence, floored at 0.7

Cross-pollinated entries re-enter the pending queue naturally and are evaluated as regular entries in the next curation cycle. No loop risk: the curator assesses signal on each pass and does not auto-cross-pollinate indefinitely.

## Step 5 — Report

Produce a curation summary (see agent output format for signal structure).

When the report includes MCP entries, add an **Entries table** with these columns:

| ID | Source | Preview | Rating | Action |
|----|--------|---------|--------|--------|
| e42 | builder | "Mock pydantic-settings models with MagicMock(spec=…)" | HIGH | Cross-pollinate → reviewer |
| e43 | test-writer | "Run tests before committing" | NOISE | Mark-for-deletion |

- **ID** — the MCP entry ID from `list_entries`
- **Source** — the `scope_agent` that wrote the entry
- **Preview** — first 80 characters of the entry content
- **Rating** — HIGH / MEDIUM / LOW / NOISE / CONFLICT
- **Action** — Promote / Keep / Mark-for-deletion / Cross-pollinate / DR-created

## Self-critique checklist

Before reporting:

- [ ] Processed all entries in scope
- [ ] Deduplicated by meaning, not just exact text match
- [ ] Promotions are genuinely actionable + non-obvious + recurring
- [ ] Noise removals are truly generic/empty (not just unfamiliar)
- [ ] Conflicts flagged, not auto-resolved
- [ ] Report statistics match actions taken
- [ ] Did not fabricate any findings
