---
approved_at: null
categories: [pitfall, domain-knowledge, tool-usage]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-17T01:38:22.436416Z'
didnt_use_count: 0
id: 8316cb94-499e-4ac7-b523-c6e34c1c0cdd
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: PDS p-button variant is a DOM property
unremarkable_count: 0
updated_at: '2026-07-14T23:51:53.009500+00:00'
---

In PDS v4 jsdom tests, `p-button` `variant` is a non-reflected DOM property, so `getAttribute('variant')` returns `null`. Assert the HTMLElement property value instead; reflected attributes like `hide-label` can still use attribute checks.
