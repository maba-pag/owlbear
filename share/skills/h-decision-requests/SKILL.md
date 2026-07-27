---
name: h-decision-requests
description: "Handbook: Create, close, and resume structured Decision and Action Requests"
user-invocable: false
---

# Decision And Action Requests

Use this handbook when a native workflow identifies one user-owned choice or action that blocks an
admitted change or engine-selected job. A request is a durable graph dependency, not a general error
report.

## Choose The Request Kind

| Kind | Use when | Required response |
|------|----------|-------------------|
| Decision Request (DR) | The user must choose among materially different valid paths | One listed option or a free-text decision |
| Action Request (AR) | The user or an explicitly invoked authorized workflow must perform an operation | A free-text outcome with the requested evidence |

Do not create a request for a transient tool failure, an ordinary implementation defect, broad
design discussion, or authority that no safe response can satisfy. The designer resolves material
Specification choices before admission; the planner may create one request only for a bounded
choice inside the admitted target.

## Create A Request

Call:

```text
create_request(
   request_id,
   created_at,
   change_id,
   delivery_digest,
  kind="decision" | "action",
  title,
  summary,
  agent,
   target_node_id=None,
   job_ids=None,
  options=None,
  body="...",
)
```

`create_request` validates the admitted revision, writes one immutable pending request, and gates
referenced native work through the engine. Reusing an identity with different content fails.

For a DR, provide 2–10 options. Each option has `option_id`, `label`, `confidence`, `recommended`,
and `rationale`; at most one is recommended. For an AR, omit options.

The body must make the request executable:

- exact decision or action required;
- why the active role cannot proceed autonomously;
- constraints, environment, or controlled data that apply;
- evidence or artifacts that must be returned;
- condition that makes the task ready to resume;
- destructive effects and cleanup, when applicable.

Do not hand-write native request records.

## Close The Active Job Attempt

After successful request creation:

1. Return the workflow's exact request-created disposition with the persisted request identity and
   resume condition.
2. Do not finish the job or write request files directly.
3. The orchestrator releases the unchanged active job identity and obtains a fresh engine plan.

If `create_request` fails validation, correct only a malformed payload. Digest, reference, or
authority contradictions are blocking findings; never create a substitute request file.

## Resolution And Resume

Resolution is user/Cockpit controlled. There is no agent-callable resolve tool. Resolution creates
durable resolved state and lets the engine recompute graph readiness.

On the resumed task:

1. Call `list_requests(change_id=..., delivery_digest=..., status="resolved")`.
2. Call `show_request(request_id=...)` for each relevant request.
3. Verify `resolution.resolved_at` and consume `selected_option_id` or `free_text` as structured
   authority. Do not parse the task-body summary as the decision source.
4. Confirm the response satisfies the request's resume condition and current revision. If it does
   not, return the workflow's blocked or Specification re-entry disposition.

Resolved decisions constrain subsequent work. Action outcomes are evidence, not automatic proof
that a node or change satisfies its acceptance boundary.
