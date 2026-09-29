---
description: "Run deterministic Delivery acquisition, worker dispatch, and Integration"
agent: orchestrator
---

Follow `w-orchestration` to acquire current Delivery work across the portfolio, dispatch bounded
Planner and Builder launches, forward their transitions unchanged, report failed launches with the
exact custody and missing-exclusion evidence, and report acquisition-provided Integration attention
unchanged until the portfolio is quiescent.

This is the portfolio entry. For one named Change, use `/continue-change <change-id>` and its Change
Continuation Entry instead of this batch loop.
