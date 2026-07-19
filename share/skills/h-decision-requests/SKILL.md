---
name: h-decision-requests
description: "Handbook: Create, close, and resume structured Decision and Action Requests"
user-invocable: false
---

# Decision And Action Requests

Use this handbook after `r-pipeline-protocol` classifies an interruption as a request. A request is
a resumable task dependency, not a general error report.

## Choose The Request Kind

| Kind | Use when | Required response |
|------|----------|-------------------|
| Decision Request (DR) | The user must choose among materially different valid paths | One listed option or a free-text decision |
| Action Request (AR) | The user or an explicitly invoked authorized workflow must perform an operation | A free-text outcome with the requested evidence |

Do not create a request for a transient tool failure, an ordinary implementation defect, or a task
contract that no safe action can satisfy. Follow the interruption matrix in `r-pipeline-protocol`.
When the user-facing shaper can resolve a question live before task dispatch, use `askQuestions`
instead of creating a blocked task and request.

## Create A Request

Call:

```text
create_request(
  task_id,
  kind="decision" | "action",
  title,
  summary,
  agent,
  options=None,
  body="...",
)
```

`create_request` atomically writes `decisions/pending/{request_id}.md` and blocks the task with
`block_reason="DR pending"`. It returns the structured request, including `request_id`. It does not
return a block reason.

For a DR, provide 2–10 options. Each option has `option_id`, `label`, `confidence`, `recommended`,
and `rationale`; at most one is recommended. For an AR, omit options.

The body must make the request executable:

- exact decision or action required;
- why the active role cannot proceed autonomously;
- constraints, environment, or controlled data that apply;
- evidence or artifacts that must be returned;
- condition that makes the task ready to resume;
- destructive effects and cleanup, when applicable.

Do not hand-write files under `.owlbear/kanban/decisions/`.

## Close The Active Work Session

After successful request creation:

1. If the task is claimed, append the current agent's Channel B note and release the claim with
   `end_work(outcome="release", note=...)`.
2. Do not call `end_work(outcome="block")`; the request already blocked the task.
3. Commit the task record and `decisions/pending/{request_id}.md`, plus any other task-owned changes,
   through the scoped commit procedure in `r-workspace-governance`.
4. A dispatched task agent returns `BLOCK #{task_id} | {request title; request_id; resume condition}`.
   Shaper reports the same state in its user-facing summary.

If `create_request` fails validation, correct the payload and retry. If the assigned Kanban request
tool is unexpectedly unreachable, use the tool-outage route from `r-pipeline-protocol`; never create
a substitute request file.

## Resolution And Resume

Resolution is user/Cockpit controlled. There is no agent-callable resolve tool. Resolution moves the
record to `decisions/resolved/`, appends a human-readable `## DR:` or `## AR:` summary to the task,
and unblocks the task when no sibling request remains pending.

On the resumed task:

1. Call `list_requests(status="resolved", task_id=...)`.
2. Call `show_request(request_id=...)` for each relevant request.
3. Verify `resolution.resolved_at` and consume `selected_option_id` or `free_text` as structured
   authority. Do not parse the task-body summary as the decision source.
4. Confirm the response satisfies the request's resume condition. If it does not, create a new
   focused request or reject an invalid task contract according to `r-pipeline-protocol`.

Resolved decisions constrain subsequent work. AR outcomes are evidence, not automatic proof that
the task AC is satisfied; builder and verifier still judge the returned evidence at their boundary.