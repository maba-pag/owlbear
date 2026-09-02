---
description: "Evaluate and address external pull-request feedback in managed Delivery custody"
---

Address PR feedback: ${input:change_id:Native Delivery Change ID}
Run mode: ${input:mode:start or resume (default: start)}

Read and follow `../skills/w-address-pr-feedback/SKILL.md`. Bind the exact Delivery Change and
open pull request before inspecting review threads. Use the `gh` CLI for GitHub review comments and
thread replies; do not use a GitHub MCP server. In `start` mode, critically evaluate every
unresolved thread, prepare Delivery review repair before editing, create one scoped commit per
accepted independent finding, and hand off with `/finalize-change <change-id>`. In `resume` mode,
skip preparation, reconcile the freshly finalized checkpoint, verify the exact PR head, and only
then reply to and resolve threads whose fixes are visible on the PR. Leave ambiguous or
authority-bound concerns unresolved.
