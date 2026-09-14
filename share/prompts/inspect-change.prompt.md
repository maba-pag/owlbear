---
description: "Inspect one Delivery Change through a read-only readiness projection"
mode: ask
tools:
  - owlbear-delivery/get_change
  - owlbear-delivery/delivery_health
---

Inspect: ${input:change_id:Native Change ID}

Use only the explicitly allowed `owlbear-delivery/get_change` and
`owlbear-delivery/delivery_health` tools. Explain the returned state: completed work, whether
finalization checks ran, current blockers, and supported interactions. Treat unavailable or blocked
state as diagnostic only. Do not use terminal, edit, dispatch, Delivery mutation, checkout repair,
raw Git, or user-run verification instructions. If the effective host exposes any other tool or
cannot enforce this read-only surface, report that inspection is unavailable rather than proceeding.
