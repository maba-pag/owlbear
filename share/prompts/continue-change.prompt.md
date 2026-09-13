---
description: "Continue one selected Delivery Change through its next acquired action"
agent: orchestrator
---

Continue: ${input:change_id:Native Change ID}

Follow the Change Continuation Entry of `w-orchestration` for exactly this Change. Observe it once
with `get_change`, pass the returned readiness basis unchanged to `acquire_change_action`, and
declare only the capabilities this session can actually dispatch. Dispatch strictly what one
`acquired` result carries: a worker launch, an issued finalization launch, or an engine action
executed only through `execute_change_action` with the acquired operation ID.

Yield on `busy`, `waiting`, and `human`; refresh the observation once on `stale`; report
`unsupported`, `unavailable`, and `terminal` results with their retained custody and preserved
failure envelope. Do not acquire portfolio work, dispatch a sibling Change, substitute a raw Delivery
mutation for a missing continuation operation, or merge, clean up, or complete anything implicitly.
