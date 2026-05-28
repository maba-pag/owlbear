---
id: d76adf88-7d89-4b8f-b413-09bfadcebc8b
title: Named observables need direct proof in smoke tests
categories:
- pitfall
- process
confidence: 0.92
state: curated
scope_agents:
- reviewer
- test-writer
- builder
source_agent: reviewer
created_at: '2026-05-28T01:20:00.635519Z'
updated_at: '2026-05-28T01:31:47.180972Z'
approved_at: null
---

When an AC names specific observables like update_source and sources_refreshed, reject task-local smoke tests that only assert coarse counts such as len(errors) or sources_refreshed. Require direct assertions on each named observable and on branch-specific side effects, especially when adjacent older tests cover only neighboring success/exception paths.
