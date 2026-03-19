---
applyTo: "docs/decisions/**"
description: "Structured async decision request process for agents running unsupervised"
---

# Decision Requests

When agents run unsupervised (6–12 hours), they cannot use `askQuestions` for blocking user decisions. This process provides an async alternative: agents write a structured decision request file, block the task, and move on to other work. The user reviews pending decisions at their convenience.

## When to create a decision request

Create a decision request when:

- A research finding recommends a feature or architectural direction the user hasn't approved
- An approach selection has multiple valid options with no clear winner
- A scope or priority decision affects multiple downstream tasks
- A feature-gate decision determines whether something should be built at all

Do NOT create a decision request for:

- Technical implementation choices within an approved scope (the architect handles these)
- Bug fixes or refactors with an obvious correct approach
- Decisions the agent can make with high confidence (≥ .85)

## File format

**Location:** `docs/decisions/pending/{task-id}-{slug}.md`

**Naming:** Use the owning task ID and a short kebab-case slug describing the decision.

```markdown
---
# >> Your action: set approved to true (edit decision/notes first if you disagree)
approved: false
decision: "A: Adopt library X"
notes: ""
# >> Agent metadata (do not edit)
task_id: 123
agent: researcher
created: 2026-03-13
urgency: blocking
decision_type: feature-gate
---

# Decision: Should we adopt library X for component Y?

## Context

1–3 paragraphs: why this decision is needed, what research was done, what task
is blocked. Link to the research doc if one exists.

## Options

### A: Adopt library X ← recommended

- Effort: ~2 days, 3 tasks
- Trade-off: adds dependency, but saves 500 LOC
- Risk: library is maintained by solo dev

### B: Build custom implementation

- Effort: ~5 days, 6 tasks
- Trade-off: no external dependency, but more code to maintain
- Risk: we reinvent solved problems

### C: Defer / do nothing

- Effort: 0
- Trade-off: feature stays unimplemented
- Risk: none immediate

## Recommendation

.80 confidence — Option A. Library X covers 90% of our requirements with minimal
integration effort. The solo-maintainer risk is mitigated by the small API surface
(we can fork if abandoned).

## Impact of Deferral

Task #123 is blocked. If no decision is made within 5 days, the planner will
auto-resolve with the recommended option (A). No downstream tasks are affected
until this is unblocked.
```

The agent **pre-fills** `decision:` with the recommended option so the user can accept by only changing `approved: false` → `approved: true`. No `## Resolution` body section is needed.

## Frontmatter fields

### User fields (top of frontmatter)

| Field      | Values                                                                   | Set by     |
| ---------- | ------------------------------------------------------------------------ | ---------- |
| `approved` | `false` (pending) / `true` (user approved) / `auto` (5-day auto-resolve) | User       |
| `decision` | Pre-filled with agent recommendation; user edits if they disagree        | Agent/User |
| `notes`    | Empty string; user may add caveats, conditions, or reasoning             | User       |

### Agent metadata (bottom of frontmatter — user should not edit)

| Field           | Values                                                                          | Set by |
| --------------- | ------------------------------------------------------------------------------- | ------ |
| `task_id`       | Kanban task ID that is blocked                                                  | Agent  |
| `agent`         | Agent that created the request                                                  | Agent  |
| `created`       | ISO date (YYYY-MM-DD)                                                           | Agent  |
| `urgency`       | `blocking` (task is parked) or `advisory` (agent continued with recommendation) | Agent  |
| `decision_type` | `feature-gate` / `approach-selection` / `scope-decision` / `priority-call`      | Agent  |

## Blocking behavior

After creating the decision request file:

1. **If other unblocked tasks exist on the board:** Block the current task and release the claim. Move on to other work.

   ```powershell
   kanban\kanban-md.exe edit {ID} --block "Decision pending: docs/decisions/pending/{id}-{slug}.md"
   ```

2. **If NO other unblocked tasks exist:** Proceed with the recommended option. Create follow-up tasks. Mark the decision request as `urgency: advisory` and `approved: auto`.

## Resolution workflow

**User accepts the recommendation:**

1. Open `docs/decisions/pending/{id}-{slug}.md`
2. Change `approved: false` → `approved: true`
3. Optionally add `notes:` (caveats, conditions)

That's it. The planner handles the rest.

**User overrides the recommendation:**

1. Open `docs/decisions/pending/{id}-{slug}.md`
2. Change `decision:` to the preferred option (e.g., `decision: "B: Build custom"`)
3. Optionally add `notes:` explaining the reasoning
4. Change `approved: false` → `approved: true`

**Alternatively**, use the CLI: `bearclaw decisions resolve {task_id}` — it prompts for choice, notes, and updates the file automatically.

**Planner detects approval:** Each planning cycle, the planner checks `docs/decisions/pending/` for files with `approved: true`. For each:

- Unblock the task: `kanban\kanban-md.exe edit {task_id} --unblock`
- Move the file to `docs/decisions/resolved/`

The user never moves files — the planner does this automatically.

**Auto-resolution (5-day timeout):** If a decision stays `approved: false` for 5+ days, the planner auto-resolves with the agent's pre-filled recommendation to prevent permanent blockage. The file is updated with `approved: auto` and the task is unblocked.

> **Legacy files:** Files using the old `status: pending/resolved` format are treated equivalently: `status: resolved` is handled the same as `approved: true`.

## Integration with existing processes

- **Researchers:** After completing research, if findings require a user decision (feature-gate, architectural direction), create a decision request instead of follow-up tasks. See `research-docs.instructions.md`.
- **Architects:** If an architecture review reveals a decision that needs user input, create a decision request and block the task.
- **Planner:** Checks `docs/decisions/pending/` at Step 1 of each wave planning cycle.
- **All agents:** The defer-to-user boundary in `agent-common.instructions.md` references this process.
