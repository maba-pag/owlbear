---
name: h-decision-requests
description: "Handbook: Decision request helper — create DR/AR records and follow lifecycle semantics"
user-invocable: false
---

# Decision Requests Handbook

Use `create_dr` to create pending decision and action requests.

Agents create DRs but do not resolve them. Resolution is a user action outside the agent pipeline.

## When To Create A DR

Do not create DRs for routine implementation details already covered by AC, protocol rules, or existing project standards. If `r-pipeline-protocol` Decision Tiers directed you here, proceed.

## create_dr Contract

Use `create_dr` with these required parameters:

- `task_id`: integer task identifier for the blocked task.
- `agent`: agent name creating the request.
- `request_type`: one of `decision` or `action`.
- `body`: markdown payload with context, options, and explicit question.

Calling `create_dr` blocks the task with reason `DR pending`.

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

After calling `create_dr`:

1. Stop active work on the task.
2. Do not poll or wait for a response.
3. Call `end_work` to release your claim (see `r-pipeline-protocol` § Escalation Routing for the correct outcome per tier).
