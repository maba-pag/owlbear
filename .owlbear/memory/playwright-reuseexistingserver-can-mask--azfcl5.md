---
id: 1b476227-0c20-420c-b2cf-264ac17d2172
title: Playwright reuseExistingServer can mask updated public assets in Cockpit E2E
categories:
- pitfall
- tool-usage
confidence: 0.89
state: curated
scope_agents:
- builder
- reviewer
- quality-runner
source_agent: builder
created_at: '2026-05-12T18:31:21.290228Z'
updated_at: '2026-05-12T21:24:50.746237Z'
approved_at: null
---

For serve/cockpit/web Playwright runs, an existing preview server on :4173 may be reused (reuseExistingServer=true outside CI), causing stale dist/public assets and false E2E timeouts. Kill the :4173 listener before reruns when diagnosing runtime asset issues or unexpected 404s in Cockpit E2E.
