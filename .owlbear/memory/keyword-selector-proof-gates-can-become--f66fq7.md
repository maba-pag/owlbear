---
id: 623dc7f6-5f66-4ad0-a979-5a9d6c628a42
title: Keyword selector proof gates can become unsatisfiable from unrelated test drift
categories:
- pitfall
- process
confidence: 0.82
state: curated
scope_agents:
- builder
- architect
source_agent: builder
created_at: '2026-05-28T08:01:57.945522Z'
updated_at: '2026-05-28T09:11:03.534459Z'
approved_at: null
---

In builder proof_bundle=existing flows, broad pytest selector gates like -k 'knowledge or enrichment ...' may pick up unrelated failing suites and block otherwise-complete tasks. If AC requires such a gate and it fails outside task scope, reject to backlog for architect to narrow gate or add explicit ignores/dependencies.
