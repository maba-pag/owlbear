---
name: decision-requests
description: "Structured async decision request process — create decision files to ask the user for input, block the task, and continue other work. Used by any agent that hits a decision point requiring user approval."
---

# Decision Requests

When agents hit a decision point that requires user input, they write a structured decision request file, block the task, and move on to other work. The user reviews pending decisions at their convenience.

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

## When to create an action request

Create an action request when you need the user to **do something** rather than **decide something**:

- Manual testing or GUI verification that cannot be automated
- Credential setup, access grants, or authentication configuration
- Deployments, releases, or operations requiring human authorization
- External actions (submitting forms, contacting third parties, etc.)
- Any step that requires direct user interaction with a system or interface

Do NOT create an action request for:

- Decisions between multiple options (use a decision request instead)
- Work the agent can perform autonomously (no user interaction required)

## Option presentation conventions (decision type only)

When presenting options in a decision request:

- Each option gets a **confidence score** (.0–1.0, no leading zero)
- Tag each option with `(bp:)` for best practice or `(rec:)` for recommendation
- List concrete **pros/cons** per option — no vague hand-waving
- Always include a **"Defer / do nothing"** option with explicit trade-offs
- Pre-fill `decision:` in frontmatter with the recommended option so the user can accept by simply changing `approved: false` → `approved: true`

## File format

**Location:** `docs/decisions/pending/{task-id}-{slug}.md`

**Naming:** Use the owning task ID and a short kebab-case slug describing the decision.

### Decision request

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
impact_tier: 2
---

# Decision: Should we adopt library X for component Y?

## Context

1–3 paragraphs: why this decision is needed, what research was done, what task
is blocked. Link to the research doc if one exists.

## Options

### A: Adopt library X ← (rec:) recommended

- Effort: ~2 days, 3 tasks
- Trade-off: adds dependency, but saves 500 LOC
- Risk: library is maintained by solo dev

### B: Build custom implementation — (bp:) best practice

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

### Action request

```markdown
---
# >> Your action: check off all steps below, then set completed to true
completed: false
notes: ""
# >> Agent metadata (do not edit)
request_type: action
task_id: 456
agent: builder
created: 2026-03-30
urgency: blocking
---

# Action Request: {title}

## Context

Why this action is needed and what task is blocked. Link to relevant task or documentation.

## Steps

- [ ] Step 1 description
- [ ] Step 2 description with expected outcome
- [ ] Step 3 — verify X shows Y

## Completion instructions

When all steps above are checked off, set `completed: true` in the YAML header.
Write your findings in the `notes:` field. If you need more space, add a section
(e.g., `## My Findings`) and reference it in `notes:` (e.g., `notes: "All passed,
see ## My Findings"`). The planner copies `notes:` — and any referenced section —
into the task body so the next agent can see what you found.
```

## Frontmatter fields

### User fields (top of frontmatter)

| Field          | Values                                                                   | Applies to | Set by     |
| -------------- | ------------------------------------------------------------------------ | ---------- | ---------- |
| `request_type` | `decision` (default, may be omitted) / `action`                          | all        | Agent      |
| `approved`     | `false` (pending) / `true` (user approved) / `auto` (5-day auto-resolve) | decision   | User       |
| `decision`     | Pre-filled with agent recommendation; user edits if they disagree        | decision   | Agent/User |
| `completed`    | `false` (pending) / `true` (user completed all steps)                    | action     | User       |
| `notes`        | Findings, caveats, or conditions. For long content, add a body section and reference it here (e.g., `"see ## My Findings"`) | all        | User       |

### Agent metadata (bottom of frontmatter — user should not edit)

| Field           | Values                                                                          | Applies to | Set by |
| --------------- | ------------------------------------------------------------------------------- | ---------- | ------ |
| `task_id`       | Kanban task ID that is blocked                                                  | all        | Agent  |
| `agent`         | Agent that created the request                                                  | all        | Agent  |
| `created`       | ISO date (YYYY-MM-DD)                                                           | all        | Agent  |
| `urgency`       | `blocking` (task is parked) or `advisory` (agent continued with recommendation) | all        | Agent  |
| `decision_type` | `feature-gate` / `approach-selection` / `scope-decision` / `priority-call`      | decision   | Agent  |
| `impact_tier`   | `1` (T1 autonomous, should not appear in practice) / `2` (T2 advisory, default) / `3` (T3 mandatory, no auto-resolve) | decision   | Agent  |

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

**Planner detects approval:** Each planning cycle, the planner checks `docs/decisions/pending/` for files with `approved: true` (decisions) or `completed: true` (action requests). For each resolved file, the planner performs three steps in order:

1. **Write summary to task body** — extracts `decision:`/`notes:` (decisions) or `notes:` (action requests) from the frontmatter and appends a `## Decision Resolved` or `## Action Completed` section to the task body via `kanban-md edit`. This is the critical step — without it, downstream agents cannot see the user's feedback.
2. **Unblock the task** — `kanban\kanban-md.exe edit {task_id} --unblock`
3. **Move the pending file** to `docs/decisions/resolved/`. If it already exists in `resolved/`, delete the `pending/` copy.

The user never moves files — the planner does this automatically.

**Auto-resolution (5-day timeout):** If an `impact_tier: 2` decision (or a decision with no `impact_tier` field) stays `approved: false` for 5+ days, the planner auto-resolves with the agent's pre-filled recommendation. The file is updated with `approved: auto` and the task is unblocked. Missing `impact_tier` defaults to tier 2 for backwards compatibility — existing files retain current auto-resolve behavior.

**T3 decisions do not auto-resolve.** When `impact_tier: 3`, the planner skips the 5-day timer entirely. These decisions block indefinitely until the user explicitly approves or overrides. Use `impact_tier: 3` for mandatory decisions: new capabilities, architecture changes, security/process changes, and breaking changes.

**T1 note:** `impact_tier: 1` outcomes are autonomous — agents proceed without user input and do not produce decision requests. The value `1` exists for completeness but should not appear in practice in decision request files.

> **Legacy files:** Files using the old `status: pending/resolved` format are treated equivalently: `status: resolved` is handled the same as `approved: true`.

### Action requests

**User completes the steps:**

1. Open `docs/decisions/pending/{id}-{slug}.md`
2. Check off each completed step in the `## Steps` section
3. Set `completed: false` → `completed: true` in the YAML header
4. Save. Done.

The planner treats `completed: true` the same as `approved: true` — it writes the
user's `notes:` to the task body (as `## Action Completed`), unblocks the task, and
moves the file to `resolved/`. See the resolution workflow above for the full
three-step process.

## Pre-flight: check for existing decisions before creating new ones

Before creating any new decision or action request, **always check for prior resolutions**:

1. Search `docs/decisions/resolved/{task-id}-*` for files matching the current task ID.
2. If a resolved decision exists:
   - **Read it.** Extract the `decision:` (user's chosen option) and `notes:` (user feedback).
   - **Apply the user's choice** to your work — do not recreate the same request.
   - If the user's notes invalidate part of the AC or change requirements, treat them as **AC amendments**: update the task body to reflect the user's constraints before proceeding.
3. Also check `docs/decisions/pending/{task-id}-*` — if a request is already pending for this task, do not create a duplicate.

> **Why this matters:** Without this check, agents re-dispatched on the same task will
> create duplicate decision requests, forcing the user to answer the same question
> repeatedly while their previous feedback is ignored.

## User notes are AC amendments

When a user resolves a decision request, their `notes:` field is not just commentary — it carries **binding constraints** for the implementation. Examples:

- "blocking is a no-go if no action is assigned" → the agent must not use BLOCK without an actionable follow-up
- "please actually read my input and make changes" → prior feedback was ignored, re-read resolved files
- "option A but only for Python files" → scope constraint that narrows the chosen approach

Agents encountering a `## Decision Resolved` section in the task body (written by the planner) or reading a resolved decision file directly must treat user notes as hard requirements, not suggestions.

## Integration with existing processes

- **Researchers:** After completing research, if findings require a user decision (feature-gate, architectural direction), create a decision request instead of follow-up tasks. See `research-workflow` skill Step 5.
- **Architects:** If an architecture review reveals a decision that needs user input, create a decision request and block the task.
- **Planner:** Checks `docs/decisions/pending/` at Step 1 of each planning cycle. Writes decision summaries to task bodies on resolution (see `dispatch-planning` skill Recipe 0).
- **All agents:** The defer-to-user boundary in `agent-common.instructions.md` references this process. All agents must run the pre-flight check in `agent-common.instructions.md` → **Resolved decision pre-flight** before starting work on any task.
