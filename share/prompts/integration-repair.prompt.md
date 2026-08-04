---
description: "Repair one current Integration merge conflict through independent exact-commit review"
agent: builder
---

Integration Repair: ${input:change_id:Delivery change ID}

Require a non-empty `change_id`, then follow `w-integration-repair` for that exact change. Do not
enumerate changes, infer another identity, run Integration, or update the Integration target.
