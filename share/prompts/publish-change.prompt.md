---
description: "Advance one finalized Delivery Change through publication and acceptance"
---

Publish: ${input:change_id:Native Change ID}

Read and follow `../skills/w-change-publication/SKILL.md`. Bind the supplied Change ID to fresh
Delivery work-item and publication authority, then perform only the next authority-safe publication
operation. Synchronize a stale target before publishing a checkpoint, never resolve merge conflicts
or move refs with raw Git, and stop at any user merge or reviewed-code boundary with the exact next
action.
