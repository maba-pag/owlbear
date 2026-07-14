---
approved_at: null
categories: [pitfall, tool-usage]
confidence: 0.88
contested_by_task: null
created_at: '2026-05-18T01:44:39.554546Z'
didnt_use_count: 0
id: ce946ee9-e063-4816-87cb-9e5a991e552e
outstanding_count: 0
scope_agents: [verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: CSS migrations can break inline-style assertions
unremarkable_count: 0
updated_at: '2026-07-14T23:57:05.002448+00:00'
---

When reviewing frontend refactors that move presentation from JSX inline styles into shared CSS, rerun the full Vitest suite. Assertions against element.style can fail even when the UI contract is preserved via stylesheet selectors, so classify these as likely test-proof gaps before assuming an implementation regression.
