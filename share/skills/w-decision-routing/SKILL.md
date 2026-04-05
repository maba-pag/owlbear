---
name: w-decision-routing
description: "Workflow: Decision routing — create, check, and resolve decision/action requests"
user-invocable: false
---

# Decision Routing

Create, check, and resolve decision and action requests. The scribe is the exclusive handler of `.owlbear/decisions/` — all agents interact with DRs through this workflow.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

This skill does NOT claim a task — the scribe operates on behalf of the calling agent. It receives three parameters: `task_id`, `mode`, and optionally `request_type`/`concern`.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Modes

### Mode 1: check-or-create

1. Search `.owlbear/decisions/pending/` and `.owlbear/decisions/resolved/` for files matching the task ID.
2. **If a resolved DR covers the same concern:** return the user's answer verbatim (decision + notes).
3. **If a pending DR covers the same concern:** return "already pending."
4. **If no match:** create the DR with proper frontmatter and block the task.

### Mode 2: resolve

Scan `.owlbear/decisions/pending/` for files where `approved: true` (decisions) or `completed: true` (action requests). For each resolved file, perform three steps in order:

1. **Write summary to task body** — extract `decision:`/`notes:` (decisions) or `notes:` (actions) and append `## Decision Resolved` or `## Action Completed` to the task body via `edit_task` (with `append_body`).
2. **Unblock the task** — via `edit_task` (with `unblock=True`).
3. **Move the pending file** to `.owlbear/decisions/resolved/`. If it already exists in `resolved/`, delete the `pending/` copy.

**Auto-resolution (5-day timeout):** `impact_tier: 2` decisions (or missing `impact_tier`) staying `approved: false` for 5+ days get auto-resolved with the agent's pre-filled recommendation. Update with `approved: auto` and unblock.

**T3 decisions do NOT auto-resolve.** `impact_tier: 3` blocks indefinitely until explicit user approval.

### Mode 3: query

Search pending and resolved DRs for the task without creating. Return findings.

## When to Create a Decision Request

Create when:

- Research finding recommends a direction the user hasn't approved.
- Multiple valid options with no clear winner.
- Scope or priority decision affects downstream tasks.
- Feature-gate decision on whether something should be built.

Do NOT create for:

- Technical choices within approved scope (architect handles these).
- Bug fixes or refactors with obvious correct approach.
- Decisions the agent can make with confidence 0.85+.

## When to Create an Action Request

Create when the user must **do something** (not decide):

- Manual testing or GUI verification.
- Credential setup, access grants.
- Deployments, releases.
- External actions (forms, contacts).

## Decision Request File Format

**Location:** `.owlbear/decisions/pending/{task-id}-{slug}.md`

### Frontmatter

```yaml
---
# >> Your action: set approved to true
approved: false
decision: "A: {recommended option}"
notes: ""
# >> Agent metadata
task_id: {id}
agent: {agent_name}
created: {YYYY-MM-DD}
urgency: blocking
decision_type: {feature-gate|approach-selection|scope-decision|priority-call}
impact_tier: {2|3}
---
```

### Body Structure

```markdown
# Decision: {question}

## Context
{1-3 paragraphs: why needed, what research, what's blocked}

## Options

### A: {option} — (rec:) recommended
- Effort: {estimate}
- Trade-off: {description}
- Risk: {description}

### B: {option} — (bp:) best practice
{...}

### C: Defer / do nothing
{...}

## Recommendation
{confidence} — {option}. {reasoning}

## Impact of Deferral
{what's blocked, auto-resolve timeline}
```

### Option Presentation Conventions

- Each option gets a confidence score (0.0–1.0).
- Tag with `(bp:)` for best practice or `(rec:)` for recommendation.
- Concrete pros/cons per option.
- Always include "Defer / do nothing" with explicit trade-offs.
- Pre-fill `decision:` with recommended option.

## Action Request File Format

```yaml
---
completed: false
notes: ""
request_type: action
task_id: {id}
agent: {agent_name}
created: {YYYY-MM-DD}
urgency: blocking
---
```

Body includes `## Context`, `## Steps` (with checkboxes), and `## Completion instructions`.

## Blocking Behavior

After creating the DR:

1. **If other unblocked tasks exist:** Block the current task via `edit_task(block="DR pending: {filename}")`. Do NOT release the claim — the calling agent does that via `end_work(outcome="block")`. Return the CREATED signal with the instruction to end work.
2. **If NO other unblocked tasks exist:** Proceed with recommended option. Mark `urgency: advisory` and `approved: auto`.

## User Notes Are AC Amendments

When a user resolves a DR, their `notes:` field carries **binding constraints** for implementation. Downstream agents must treat user notes as hard requirements.

## Output Template

Channel A signal:

```
DONE #{task_id} -> {status} | {mode}: {result summary}
```

## Verification Checklist

- [ ] In check-or-create mode: searched BOTH pending and resolved folders
- [ ] In check-or-create mode: existing DR actually covers the same concern (not different aspect)
- [ ] In resolve mode: wrote `## Decision Resolved` or `## Action Completed` to EVERY resolved task's body
- [ ] In resolve mode: moved EVERY processed file from pending to resolved
- [ ] In resolve mode: unblocked EVERY task with a resolved DR
- [ ] T3 decisions not auto-resolved (only T2 and unspecified tiers)
- [ ] Returned exactly one Channel A signal line
- [ ] No duplicate DRs created for the same concern

## Known Pitfalls

- **Duplicate detection failure:** Without checking both pending AND resolved folders, agents re-dispatched on the same task create duplicate DRs. The user answers the same question repeatedly.
- **Same task, different concern:** Two DRs for the same task are valid if they cover different concerns. Match on concern content, not just task ID.
- **T3 auto-resolution:** Impact tier 3 decisions NEVER auto-resolve. A 5-day timer on a T3 decision silently bypasses mandatory user approval.
- **Missing body write in resolve mode:** The critical step is writing `## Decision Resolved` to the task body. Without it, downstream agents cannot see the user's feedback — the file move alone is insufficient.
- **Stale pending files:** Files that were manually resolved (moved to resolved) but still have copies in pending cause double-processing. Check for duplicates.
