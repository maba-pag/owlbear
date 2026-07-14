---
approved_at: null
categories: [tool-usage, process]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-28T08:41:24.861707Z'
didnt_use_count: 0
id: a2b6b6a9-79d4-43f4-9a4e-02c962595996
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: quality-runner supports pytest selector strings in test_paths
unremarkable_count: 0
updated_at: '2026-07-14T20:36:36.159305+00:00'
---

For proof_bundle=existing tasks, quality-runner mode=scoped accepts a full pytest selector string (including -k and --ignore flags) inside a single test_paths entry, which is useful for AC-locked regression gates.
