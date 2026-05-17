---
id: 8316cb94-499e-4ac7-b523-c6e34c1c0cdd
title: PDS p-button variant is a DOM property
categories:
- pitfall
- domain-knowledge
- tool-usage
confidence: 0.82
state: curated
scope_agents:
- test-writer
- reviewer
- builder
source_agent: copilot
created_at: '2026-05-17T01:38:22.436416Z'
updated_at: '2026-05-17T01:48:31.919091Z'
approved_at: null
---

In PDS v4 jsdom tests, `p-button` `variant` is a non-reflected DOM property, so `getAttribute('variant')` returns `null`. Assert the HTMLElement property value instead; reflected attributes like `hide-label` can still use attribute checks.
