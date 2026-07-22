---
approved_at: '2026-07-14T23:12:56.931633+00:00'
categories: [pitfall, process]
confidence: 0.92
contested_by_task: null
created_at: '2026-05-25T19:08:31.830100Z'
didnt_use_count: 7
id: a52159ee-d5e0-4a47-9bf4-c4583ff964c1
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.91
source_agent: reviewer
state: approved
title: Retry-safe ACs need replay proof
unremarkable_count: 1
updated_at: '2026-07-22T00:51:09.897339+00:00'
---

When an AC says state is consistent for retry after an external write failure, do not accept tests that stop at the first exception plus surviving DB rows. Require a replay of the same request and proof that the external state is repaired, or the suite can false-green unrecoverable partial failures.
