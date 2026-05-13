---
name: h-decision-requests
description: "Handbook: Decision request helper — create DR/AR records and follow lifecycle semantics"
user-invocable: false
---

# Decision Requests Handbook

Use the decision-request helper to create decision and action requests:

- `create_dr(...)`: create pending DR/AR records in `.owlbear/kanban/decisions/`

`create_dr` has no query mode, and agents do not resolve DR/AR files. `pick_tasks` is read-only: it excludes blocked tasks and does not apply pending responses. Decision resolution is handled through the Cockpit decision flow, which appends a `## Decision Request` summary for both decision and action requests, unblocks tasks when appropriate, and moves resolved files out of pending. Use `response: approved` when a requested user action is complete.

## When To Create A DR

Create a DR (or AR) when the current agent cannot safely continue without a
user choice or external action.

Typical triggers:

- A task is blocked by ambiguous requirements with more than one valid path.
- A policy or architecture choice could invalidate downstream work.
- User intervention is required (credentials, approvals, manual step).
- A retry/fix strategy has product or workflow impact that must be confirmed.

Do not create DRs for routine implementation details that are already covered
by AC, protocol rules, or existing project standards.

## create_dr Contract

Use `create_dr` with these required parameters:

- `task_id`: integer task identifier for the blocked task.
- `agent`: agent name creating the request.
- `request_type`: one of `decision` or `action`.
- `body`: markdown payload with context, options, and explicit question.

The helper writes a pending file under `.owlbear/kanban/decisions/pending/` and
blocks the task with reason `DR pending`.

## Body Format

Structure the `body` as concise markdown with three parts:

1. Context: what is blocked and why now.
2. Options: 2-4 concrete options with trade-offs.
3. Question: explicit decision prompt to resolve the block.

Recommended skeleton:

```markdown
## Context
- Task: #{id}
- Blocker: {short description}

## Options
1. Option A: {summary, pros/cons}
2. Option B: {summary, pros/cons}

## Decision Needed
Please choose one option and provide any constraints.
```

## Fire-And-Forget Semantics

DR creation is fire-and-forget:

- Create the request and stop active work on the task.
- Do not poll or wait in-loop for a response.
- Release/park per pipeline protocol; the task stays blocked until a user resolves the DR/AR.
- The next orchestration pick-up sees the task only after resolution has already unblocked it.

Resolution flow:

- A user resolves the DR/AR through Cockpit with `approved`, `needs-info`, or `rejected`.
- Resolution appends the `## Decision Request` summary, moves the file to resolved, and unblocks the task when the response indicates continuation.
- The next `pick_tasks` cycle can dispatch the unblocked task.

## Operational Rules

- Never write `.owlbear/kanban/decisions/` files directly.
- Use helper operations to keep DR lifecycle behavior consistent.
- Use `create_dr` for both advisory and mandatory requests.
