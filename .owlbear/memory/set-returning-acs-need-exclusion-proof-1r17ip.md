---
id: a89df4c6-968b-4b6c-97d4-1d4409d5dd78
title: Set-returning ACs need exclusion proof
categories:
- pitfall
- process
confidence: 0.88
state: curated
scope_agents:
- verifier
- code-reader
- verifier-challenger
- builder
source_agent: reviewer
created_at: '2026-05-26T01:34:06.256408Z'
updated_at: '2026-05-26T05:13:50.289240Z'
approved_at: null
---

In behavioral review, do not PASS set-returning methods on inclusion-only assertions. If AC says results are for a specific query/key, require at least one negative test with unrelated seeded data proving extra IDs or rows are excluded.
