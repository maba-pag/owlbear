---
id: 3434d792-5d49-4739-9965-f849ea9d4cea
title: Threshold ACs need exact-edge proof
categories:
- pitfall
- process
confidence: 0.94
state: curated
scope_agents:
- reviewer
- code-reader
- challenger
source_agent: reviewer
created_at: '2026-05-26T01:41:31.964518Z'
updated_at: '2026-05-26T05:13:50.343923Z'
approved_at: null
---

When an AC specifies an exact threshold like 'exceeds 600s', do not PASS on tests that cover only clearly-stale and clearly-fresh cases. Require one task-local assertion at the exact boundary or the suite can false-green under both strict and inclusive comparisons.
