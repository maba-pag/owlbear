---
approved_at: null
categories: [pitfall, process]
confidence: 0.92
contested_by_task: null
created_at: '2026-05-28T01:20:00.635519Z'
didnt_use_count: 0
id: d76adf88-7d89-4b8f-b413-09bfadcebc8b
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: reviewer
state: deleted
title: Named observables need direct proof in smoke tests
unremarkable_count: 0
updated_at: '2026-07-14T21:05:36.883713+00:00'
---

When an AC names specific observables like update_source and sources_refreshed, reject task-local smoke tests that only assert coarse counts such as len(errors) or sources_refreshed. Require direct assertions on each named observable and on branch-specific side effects, especially when adjacent older tests cover only neighboring success/exception paths.
