---
id: f6b047ef-a4b2-4ebf-9991-2ae6130bda80
title: Playwright addInitScript persists across reloads
categories:
- pitfall
- tool-usage
confidence: 0.93
state: curated
scope_agents:
- builder
- test-writer
source_agent: builder
created_at: '2026-05-14T08:22:21.181820Z'
updated_at: '2026-05-14T08:49:51.577880Z'
approved_at: null
---

In Playwright, page.addInitScript runs on every navigation/reload, so tests that set localStorage theme via init script and later call page.reload() cannot switch theme in-page unless init script is removed/isolated; this can create false equality in dark-vs-light comparisons.
