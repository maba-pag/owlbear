---
approved_at: null
categories: [pitfall, process]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-28T08:01:57.945522Z'
didnt_use_count: 0
id: 623dc7f6-5f66-4ad0-a979-5a9d6c628a42
outstanding_count: 0
scope_agents: [builder, shaper]
score: 0.0
source_agent: builder
state: deleted
title: Keyword selector proof gates can become unsatisfiable from unrelated test
  drift
unremarkable_count: 0
updated_at: '2026-07-14T20:23:39.044037+00:00'
---

In builder proof_bundle=existing flows, broad pytest selector gates like -k 'knowledge or enrichment ...' may pick up unrelated failing suites and block otherwise-complete tasks. If AC requires such a gate and it fails outside task scope, reject to backlog for architect to narrow gate or add explicit ignores/dependencies.
