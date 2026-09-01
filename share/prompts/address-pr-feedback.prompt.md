---
description: "Evaluate and address external pull-request feedback in managed Delivery custody"
---

Address PR feedback: ${input:change_id:Native Delivery Change ID}

Read and follow `../skills/w-address-pr-feedback/SKILL.md`. Bind the exact Delivery Change and
open pull request before inspecting review threads. Use the `gh` CLI for GitHub review comments and
thread replies; do not use a GitHub MCP server. Critically evaluate every unresolved thread before
editing, create one scoped commit per accepted independent finding, reply with the commit identity
and proof, resolve only answerable conversations, and leave ambiguous or authority-bound concerns
unresolved. Use Delivery's `prepare_review_repair` operation before the first edit, then hand off
with `/finalize-change <change-id>` after the managed worktree repairs are committed.
