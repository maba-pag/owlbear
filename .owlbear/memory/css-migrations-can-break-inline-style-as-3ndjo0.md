---
id: ce946ee9-e063-4816-87cb-9e5a991e552e
title: CSS migrations can break inline-style assertions
categories:
- pitfall
- tool-usage
confidence: 0.88
state: curated
scope_agents:
- verifier
source_agent: reviewer
created_at: '2026-05-18T01:44:39.554546Z'
updated_at: '2026-05-18T02:13:24.800491Z'
approved_at: null
---

When reviewing frontend refactors that move presentation from JSX inline styles into shared CSS, rerun the full Vitest suite. Assertions against element.style can fail even when the UI contract is preserved via stylesheet selectors, so classify these as likely test-proof gaps before assuming an implementation regression.
