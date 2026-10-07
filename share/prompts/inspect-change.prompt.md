---
description: "Inspect one Delivery Change through a read-only readiness projection"
agent: agent
tools:
  - owlbear-delivery/get_change
  - owlbear-delivery/delivery_health
---

Inspect: ${input:change_id:Native Change ID}

Call `owlbear-delivery/get_change` for this Change ID, then `owlbear-delivery/delivery_health`.
If either tool is deferred, load it with one tool search whose query is exactly `get_change` or
`delivery_health`; call no other tool. Explain the returned state: completed work, whether
finalization checks ran, current blockers with any readiness `retry_history` failure codes, and
supported interactions. Treat unavailable or blocked state as diagnostic only. Do not use terminal,
edit, dispatch, Delivery mutation, checkout repair, raw Git, or user-run verification instructions.
If either Delivery tool remains uncallable, report that inspection is unavailable rather than
proceeding.
