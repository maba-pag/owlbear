---
approved_at: null
categories: [pitfall, process, domain-knowledge]
confidence: 0.85
contested_by_task: null
created_at: '2026-05-25T22:46:43.189054Z'
didnt_use_count: 0
id: 519d1835-1106-403d-8645-cf9347694ca4
outstanding_count: 0
scope_agents: [verifier, code-reader, verifier-challenger]
score: 0.0
source_agent: reviewer
state: deleted
title: Omitted-if-empty ACs need negative proof
unremarkable_count: 0
updated_at: '2026-07-14T23:06:18.237066+00:00'
---

When an AC says a field or text is omitted if empty, do not PASS on a positive-only assertion for the non-empty branch. Require at least one test that would fail if an empty input rendered visible fallback text or otherwise violated the omission clause.
