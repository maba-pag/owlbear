---
approved_at: null
categories: [pitfall, process]
confidence: 0.88
contested_by_task: null
created_at: '2026-05-26T01:34:06.256408Z'
didnt_use_count: 0
id: a89df4c6-968b-4b6c-97d4-1d4409d5dd78
outstanding_count: 0
scope_agents: [verifier, code-reader, verifier-challenger, builder]
score: 0.0
source_agent: reviewer
state: deleted
title: Set-returning ACs need exclusion proof
unremarkable_count: 0
updated_at: '2026-07-14T22:57:33.228566+00:00'
---

In behavioral review, do not PASS set-returning methods on inclusion-only assertions. If AC says results are for a specific query/key, require at least one negative test with unrelated seeded data proving extra IDs or rows are excluded.
