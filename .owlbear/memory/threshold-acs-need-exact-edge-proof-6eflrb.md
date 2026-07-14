---
approved_at: null
categories: [pitfall, process]
confidence: 0.94
contested_by_task: null
created_at: '2026-05-26T01:41:31.964518Z'
didnt_use_count: 0
id: 3434d792-5d49-4739-9965-f849ea9d4cea
outstanding_count: 0
scope_agents: [verifier, code-reader, verifier-challenger]
score: 0.0
source_agent: reviewer
state: deleted
title: Threshold ACs need exact-edge proof
unremarkable_count: 0
updated_at: '2026-07-14T22:55:19.274412+00:00'
---

When an AC specifies an exact threshold like 'exceeds 600s', do not PASS on tests that cover only clearly-stale and clearly-fresh cases. Require one task-local assertion at the exact boundary or the suite can false-green under both strict and inclusive comparisons.
