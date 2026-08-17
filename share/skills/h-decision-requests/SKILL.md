---
name: h-decision-requests
description: "Handbook: Create, close, and resume structured Decision and Action Requests"
user-invocable: false
---

# Decision And Action Requests

Use this handbook when an acquired Delivery worker identifies one authority-compatible choice or action that
blocks its active outcome. A request is a durable graph dependency, not a general error report.

## Choose The Request Kind

| Kind | Use when | Required response |
| --- | --- | --- |
| Decision Request (DR) | The user must choose among materially different valid paths | One listed option or a free-text decision |
| Action Request (AR) | The user or an explicitly invoked authorized workflow must perform an operation | A free-text outcome with the requested evidence |

Do not create a request for a transient tool failure, an ordinary implementation defect, broad
design discussion, or authority that no safe response can satisfy. Designer resolves material
Design choices before admission; Planner or Builder may embed one request only for a bounded choice
inside the active outcome.

## Embed A Request In A Block

The active Planner or Builder owns one `BlockDelivery` transition. Populate its `request` with:

- `request_id` — one stable identity;
- `kind` — `decision` or `action`;
- `outcome_id` — the active outcome;
- `summary` — the exact bounded choice or action;
- `options` — unique `{option_id, label}` entries for a decision, empty for an action. Prefer two or
   more genuine alternatives; one concrete recommended proposal is valid when free text can reject,
   modify, or replace it. Never invent a meaningless second option;
- `resolution` — absent on creation.

The enclosing block supplies:

- exact decision or action required;
- why the active role cannot proceed autonomously;
- evidence or artifacts that must be returned;
- condition that makes the task ready to resume;
- source locators and optional resumable commit.

Return the block to Orchestrator. It forwards the unchanged transition to `transition_delivery`,
which persists the request and gates the outcome. Do not call a separate request tool or hand-write
request records.

## Resolution And Resume

Resolution is user/Cockpit controlled. It updates the durable request and lets Delivery recompute
readiness; workers do not invoke a resolution tool.

On a newly acquired resumed claim:

1. Read `DeliveryPlanContext.requests` or `DeliveryBuildContext.requests` from the public context
   operation.
2. Match the relevant request identity and consume `resolution.selected_option_id` or
   `resolution.response_text` as structured authority.
3. Confirm the answer satisfies the block's resume condition and current context. If not, return a
   new worker-owned `block` or a `return` to Design.

Resolved decisions constrain subsequent work. Action outcomes are evidence, not automatic proof
that a node or change satisfies its acceptance boundary.
