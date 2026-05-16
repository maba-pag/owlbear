---
id: b12b090f-0d3d-42d3-81f8-d90fa9d264ef
title: Markdown tables cannot contain raw union pipes in a single cell
categories:
- pitfall
- tool-usage
confidence: 0.84
state: curated
scope_agents:
- builder
- reviewer
- doc-writer
source_agent: builder
created_at: '2026-05-16T13:34:02.334021Z'
updated_at: '2026-05-16T13:47:52.169499Z'
approved_at: null
---

In skill/docs markdown tables, example literals containing `|` (such as TypeScript union values) must be escaped or rewritten; otherwise markdownlint MD056 reports too many cells. For proof tasks, rewrite union examples to comma-separated values to keep table column counts stable.
