---
name: curation-workflow
description: "Knowledge curation workflow: gather recent entries → deduplicate → assess signal → promote/prune/flag → report. Used by the curator agent."
---

# Curation Workflow

Step-by-step process for maintaining institutional memory — deduplicating,
consolidating, and pruning lessons learned from agent task notes.

## kanban-md Commands

| Action | Command |
|--------|---------|
| Read task (if dispatched with ID) | `kanban\kanban-md.exe show {id}` |
| Append report (if dispatched with ID) | `kanban\kanban-md.exe edit {id} -a "## Curation\n{content}" -t` |

Most curator work uses the memory tool, not kanban-md. These commands are only needed when dispatched with a specific curation task ID. See kanban-md skill for claiming protocol and pitfalls.

## Step 1 — Gather inbox entries

Review unreviewed lessons from the repo memory inbox:

1. List inbox: `memory view /memories/repo/inbox/`
2. Read each file in the inbox
3. Also check task bodies (`kanban\kanban-md.exe show {id}`) for any inline agent notes
   that weren't written to the inbox (legacy pattern)
4. Filter to the scope specified (all, last N tasks, tag filter)
5. Collect all entries

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
   "Tests should be good" = low signal. "Mock PydanticAI deps with `MagicMock(spec=...)` to avoid runtime type errors" = high signal.
2. **Non-obvious?** — Would a competent developer already know this?
   "Use type hints" = obvious. "Coverage.py MRO crash when using dotted module names with --cov" = non-obvious.
3. **Recurring?** — Has this come up more than once? Recurring findings are stronger signals.
4. **Contradicts existing?** — Does it conflict with a `reviewed` lesson?

Rate each: **HIGH** / **MEDIUM** / **LOW** / **NOISE** / **CONFLICT**

## Step 4 — Act

Based on assessment:

| Rating                                    | Action                                                     |
| ----------------------------------------- | ---------------------------------------------------------- |
| HIGH (recurring, actionable, non-obvious) | Propose changes to instructions, skills, or agent files    |
| MEDIUM (actionable but single occurrence) | Keep in inbox for next curation cycle                      |
| LOW (vaguely useful but not actionable)   | Delete from inbox                                          |
| NOISE (obvious, generic, or empty)        | Delete from inbox                                          |
| CONFLICT (contradicts existing rule)      | Create a **decision request** — do NOT auto-resolve        |
| UNCERTAIN (needs user opinion, not data)  | Create a **decision request** — do NOT keep for next cycle |

For HIGH findings: identify which file to change (instruction, skill, or agent) and
propose the specific edit. Write the proposal to the curation report. After user
approval, make the change and delete the inbox entry.

For CONFLICT / UNCERTAIN findings: create a decision request file in
`docs/decisions/pending/` following the `decision-requests` skill. Present the
conflicting entries or the uncertain finding as options, include your confidence
scores, and pre-fill the recommended disposition. If a curation task ID exists,
block it with a reference to the decision file. The planner will unblock it once
the user resolves the decision.

For deletions: `memory delete /memories/repo/inbox/{filename}`

## Step 5 — Report

Produce a curation summary (see agent output format for signal structure).

## Self-critique checklist

Before reporting:

- [ ] Processed all entries in scope
- [ ] Deduplicated by meaning, not just exact text match
- [ ] Promotions are genuinely actionable + non-obvious + recurring
- [ ] Noise removals are truly generic/empty (not just unfamiliar)
- [ ] Conflicts flagged, not auto-resolved
- [ ] Report statistics match actions taken
- [ ] Did not fabricate any findings
