---
name: h-decision-requests
description: "Handbook: Decision request helpers — create and resolve DR/AR records"
user-invocable: false
---

# Decision Requests Handbook

Use these helper operations for decision and action requests:

- `create_dr(...)`: create or query DR/AR records in `.owlbear/decisions/`
- `resolve_decision(...)`: resolve responded DR/AR records and append task summaries

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

The helper writes a pending file under `.owlbear/decisions/pending/` and
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
- Release/park per pipeline protocol (task stays blocked).
- The next orchestration pick-up resolves status after a response is recorded.

Resolution flow:

- A response is written to the DR file.
- `resolve_decision(...)` moves resolved files and appends a summary.
- Tasks are unblocked automatically when the resolution indicates continuation.

## Operational Rules

- Never write `.owlbear/decisions/` files directly.
- Use helper operations to keep DR lifecycle behavior consistent.
- Use `create_dr` for both advisory and mandatory requests.
