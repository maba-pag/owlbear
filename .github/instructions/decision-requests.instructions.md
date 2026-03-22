---
applyTo: "docs/decisions/**"
description: "Structured async decision request process for agents running unsupervised"
---

# Decision Requests

See the `decision-requests` skill for the full process, file format, and resolution workflow.

Key points:

- **Location:** `docs/decisions/pending/{task-id}-{slug}.md`
- **User action:** Set `approved: true` in frontmatter to accept recommendation
- **Auto-resolution:** Unresolved decisions auto-resolve after 5 days with agent's recommendation
- **Option conventions:** Each option gets a confidence score, `(bp:)` for best practice, `(rec:)` for recommendation
