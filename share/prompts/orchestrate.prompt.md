---
description: "Run deterministic Delivery acquisition, worker dispatch, and Integration"
agent: orchestrator
---

Follow `w-orchestration` to acquire current Delivery work across the portfolio, dispatch bounded
Planner and Builder launches, forward their transitions unchanged, recover exact failed launches,
and report acquisition-provided Integration attention unchanged until the portfolio is quiescent.
