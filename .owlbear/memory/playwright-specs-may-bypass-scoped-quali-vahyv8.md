---
approved_at: null
categories: [pitfall, tool-usage, domain-knowledge]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-17T01:38:57.066985Z'
didnt_use_count: 0
id: e91d3cdb-b6a9-47de-aaba-8409449446cd
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: copilot
state: deleted
title: Playwright specs may bypass scoped quality-runner paths
unremarkable_count: 0
updated_at: '2026-07-14T23:52:17.516322+00:00'
---

OwlBear quality-runner scoped frontend runs can match `src/**/*.{test,spec}.{ts,tsx}` while Playwright specs live under `serve/cockpit/web/e2e/`, yielding `0 collected`. Treat that as a runner path mismatch and run the Playwright proof through the frontend e2e command when the AC names an e2e spec.
