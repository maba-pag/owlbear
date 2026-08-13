---
description: "Prove and finalize one exact reviewed Delivery Change head"
agent: finalizer
---

Finalize: ${input:change_id:Native Change ID}

Read and follow `w-change-finalization`. Use the supplied Change ID, resolve fresh
`show_finalization_context`, capture relevant exact-head observations in the one managed Change
worktree, obtain an independent `review_mode: finalization` exact-commit review, and call
`finalize_change` only when every identity and cleanliness check still matches. Do not ask for
approval, create another worktree, mutate target refs, publish the checkpoint, mark the pull request
ready, or observe acceptance.
