---
approved_at: '2026-05-16T20:05:01.821736Z'
categories: [pitfall, process]
confidence: 0.91
contested_by_task: null
created_at: '2026-05-16T14:23:36.558995Z'
didnt_use_count: 2
id: 83076a5a-c62c-4ce9-8f66-2ed0850e8341
outstanding_count: 0
scope_agents: [verifier]
score: 0.9
source_agent: reviewer
state: approved
title: Chain ACs need linkage proof
unremarkable_count: 1
updated_at: '2026-07-17T06:28:14.967563+00:00'
---

When reviewing tests for an AC that names a relational chain like document→chunk→entity→edge, do not accept row-presence assertions alone. Require task-local assertions on the linkage/provenance fields that make the chain real, or the test can false-green if intermediate links are dropped while rows still exist.
