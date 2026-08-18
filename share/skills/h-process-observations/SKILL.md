---
name: h-process-observations
description: "Handbook: Triggered process observations beside exact Delivery evidence"
user-invocable: false
---

# Process Observations

Use this handbook to preserve exceptional process learning beside, but outside, exact Delivery
evidence. It is optional and should not run for an ordinary successful task with no useful process
signal.

## Boundary

- A process observation is advisory learning, not Delivery authority.
- Never edit a task, frontier, receipt, review, transition, or finalization to store process prose.
- Never use a process observation as proof of implementation, acceptance, publication, or a lifecycle
  transition.
- Bind the note to the exact Change and task or finalization identity; include the reviewed exact
  commit when one exists.

## Triggers

Create a sidecar only when at least one trigger is present:

- a reviewed result exposes material plan/result divergence;
- a retry, return, block, or review finding reveals reusable process friction;
- an unexpected workaround, missing authority, or loading problem is likely to recur;
- the user explicitly requests process learning to be preserved.

Do not create a note solely because a task completed, a command produced output, or a receipt exists.
An unsuccessful attempt without a reviewed exact-commit result remains represented by its typed
Delivery transition; a later reviewed result may record the earlier trigger as context.

## Placement And Identity

Use `.owlbear/scratch/{task-id}-process-observation.md` for working notes and delete it before task
closure. Preserve a note in `.owlbear/research/{slug}.md` only when it has durable value beyond the
active Change, following `w-research` and workspace attribution rules. Use a filesystem-safe slug.

Every preserved note names:

- Change ID;
- task, result, or finalization ID;
- reviewed exact commit, when applicable;
- trigger and observer identity;
- timezone-aware observation time;
- evidence locators;
- proposed owner or explicit no-action disposition.

## Note Template

```markdown
# Process Observation: {short title}

- Change: `{change_id}`
- Task or finalization: `{task_or_finalization_id}`
- Result: `{result_id or none}`
- Exact commit: `{40-character commit or none}`
- Trigger: `{retry | return | block | review-finding | divergence | explicit-request}`
- Observer: `{identity}`
- Observed at: `{ISO-8601 timestamp}`

## Facts

- {observable fact with a locator}

## Interpretation

- {bounded explanation, clearly separate from the fact}

## Follow-up

- Owner: {owner or none}
- Action: {smallest proposed action or no action}
- Confidence: {high | medium | low}
```

Keep facts, interpretation, and follow-up separate. Cite receipts, transitions, review findings,
files, or commands instead of copying their contents. Redact incidental user or session detail.
