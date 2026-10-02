---
description: "Run deterministic Delivery acquisition, worker dispatch, and Integration"
agent: orchestrator
---

Follow `w-orchestration` to acquire current Delivery work across the portfolio and dispatch bounded
Planner and Builder launches. Settle normally returned Planner retries and Builder retry/block/
Planning-or-Design-return transitions. Settle returned Planner/Builder no-results with
`ended-without-result` only after the dispatch returned and owned mutating work settled; preserve
launch identities and omit the request. Re-observe with `get_change`, report the receipt, and do not
dispatch a replacement in the same cycle. Delivery handles previous-session worker loss during
acquisition; report `worker-stall-wait` with `next_eligible_at` and yield. Within the current session,
do not settle an unreturned dispatch yourself. If the user explicitly states that a specific worker
chat was stopped, use `release_stuck_worker` once with its exact acquisition or `get_change` identity;
report `ERR_DELIVERY_WORKER_ACTIVE` and its retry time unchanged, and do not dispatch a replacement in
that cycle. `worker-host-lost` and `worker-released-stuck` are engine-only. A lost or released Finalizer
without a report gets `finalizer-ended-without-report` with unknown checks, not proof. Forward other
supported transitions unchanged and report Integration attention unchanged until the portfolio is
quiescent.

This is the portfolio entry. For one named Change, use `/continue-change <change-id>` and its Change
Continuation Entry instead of this batch loop.
