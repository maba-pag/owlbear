---
description: "Resolve one exact integration-target conflict in managed Delivery custody"
---

Resolve target conflict: ${input:change_id:Native Delivery Change ID}

Read and follow `../skills/w-target-conflict-resolution/SKILL.md`. Bind the current Change and
configured target head before using Delivery synchronization. Resolve only the preserved conflict
inside the managed Change worktree, call Delivery to validate and commit the merge, and stop with
`/finalize-change <change-id>` as the next command. Do not edit the primary checkout, target branch,
GitHub pull request contents, or Delivery runtime files by hand.
