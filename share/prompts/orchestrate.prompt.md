---
description: "Run deterministic Delivery acquisition, worker dispatch, and Integration"
agent: orchestrator
---

Follow `w-orchestration` to acquire current Delivery work across the portfolio and dispatch bounded
Planner and Builder launches. Settle normally returned Planner retries and Builder retry/block/
Planning-or-Design-return transitions. Settle returned Planner/Builder no-results with
`ended-without-result` only after the dispatch returned and owned mutating work settled; preserve
launch identities and omit the request. Re-observe with `get_change`, report the receipt, and do not
dispatch a replacement in the same cycle. Unreturned or possibly running work stays contained; do
not settle, recover, or redispatch it. Finalizer remains report-backed; a Finalizer that ends without
a report stays contained. Forward other supported transitions unchanged and report Integration
attention unchanged until the portfolio is quiescent.

This is the portfolio entry. For one named Change, use `/continue-change <change-id>` and its Change
Continuation Entry instead of this batch loop.
