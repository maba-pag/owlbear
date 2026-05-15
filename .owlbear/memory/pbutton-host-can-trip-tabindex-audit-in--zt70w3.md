---
id: 95087ccf-6752-4473-9570-cf398fd4b5b6
title: PButton host can trip tabIndex audit in Playwright
categories:
- pitfall
- domain-knowledge
confidence: 0.83
state: curated
scope_agents:
- builder
- reviewer
- test-writer
source_agent: builder
created_at: '2026-05-15T21:38:17.098343Z'
updated_at: '2026-05-15T22:16:55.186774Z'
approved_at: null
---

In cockpit e2e AC-7 audits that query p-button hosts for tabIndex=-1, replacing native controls with PButton may introduce false failures because host elements can expose negative tabIndex. Prefer semantic anchors/role links for non-button references when AC-2c only gates native button/input counts.
