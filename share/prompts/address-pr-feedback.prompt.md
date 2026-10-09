---
description: "Evaluate and address external pull-request feedback in managed Delivery custody"
---

Address PR feedback: ${input:change_id:Native Delivery Change ID}
Optional mode (omit to derive it from current Delivery and PR state): ${input:mode:}

Read and follow `../skills/w-address-pr-feedback/SKILL.md`. Bind the exact Delivery Change and
open pull request before inspecting review threads. Use the `gh` CLI for GitHub review comments and
thread replies; do not use a GitHub MCP server. Step 0 derives `start-reentry`, `start`, or `resume`
before mutation. An omitted mode is derived; a supplied value must be `start` or `resume` and match
the derived phase, or the workflow refuses before mutation with
`/address-pr-feedback <change-id>`. In `start`, critically evaluate unresolved threads, prepare
review repair before editing, create one scoped commit per accepted independent finding, and hand
off with `/finalize-change <change-id>`. In `resume`, reconcile the freshly finalized checkpoint,
verify the exact PR head, then reply to and resolve only after a settled viewer-authored marker is
observed. Leave ambiguous or authority-bound concerns unresolved.
