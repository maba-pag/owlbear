---
id: a52159ee-d5e0-4a47-9bf4-c4583ff964c1
title: Retry-safe ACs need replay proof
categories:
- pitfall
- process
confidence: 0.92
state: curated
scope_agents:
- verifier
- builder
source_agent: reviewer
created_at: '2026-05-25T19:08:31.830100Z'
updated_at: '2026-05-25T20:46:41.764628Z'
approved_at: null
---

When an AC says state is consistent for retry after an external write failure, do not accept tests that stop at the first exception plus surviving DB rows. Require a replay of the same request and proof that the external state is repaired, or the suite can false-green unrecoverable partial failures.
