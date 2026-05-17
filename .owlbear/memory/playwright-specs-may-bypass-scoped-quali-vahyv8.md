---
id: e91d3cdb-b6a9-47de-aaba-8409449446cd
title: Playwright specs may bypass scoped quality-runner paths
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.82
state: curated
scope_agents:
- reviewer
- builder
- test-writer
source_agent: copilot
created_at: '2026-05-17T01:38:57.066985Z'
updated_at: '2026-05-17T01:48:32.148604Z'
approved_at: null
---

OwlBear quality-runner scoped frontend runs can match `src/**/*.{test,spec}.{ts,tsx}` while Playwright specs live under `serve/cockpit/web/e2e/`, yielding `0 collected`. Treat that as a runner path mismatch and run the Playwright proof through the frontend e2e command when the AC names an e2e spec.
