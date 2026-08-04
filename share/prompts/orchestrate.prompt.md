---
description: "Run deterministic Delivery acquisition, worker dispatch, and Integration"
agent: orchestrator
---

Follow `w-orchestration` to acquire current Delivery work across the portfolio, dispatch bounded
Planner and Builder launches, forward their transitions unchanged, recover exact failed launches,
and invoke only acquisition-provided Integration IDs until the portfolio is quiescent.
