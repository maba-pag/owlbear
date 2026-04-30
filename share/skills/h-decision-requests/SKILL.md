---
name: h-decision-requests
description: "Handbook: Decision request helpers — create and resolve DR/AR records"
user-invocable: false
---

# Decision Requests Handbook

Use these helper operations for decision and action requests:

- `create_dr(...)`: create or query DR/AR records in `.owlbear/decisions/`
- `resolve_decision(...)`: resolve responded DR/AR records and append task summaries

Rules:

- Never write `.owlbear/decisions/` files directly.
- Use helper operations to keep DR lifecycle behavior consistent.
- Use `create_dr` for both advisory and mandatory requests.
