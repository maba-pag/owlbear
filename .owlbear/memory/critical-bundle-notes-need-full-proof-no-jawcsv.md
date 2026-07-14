---
approved_at: null
categories: [process, pitfall]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-18T01:44:39.570225Z'
didnt_use_count: 0
id: 9e6876b5-2ce6-4cd4-87bd-c82f431295d5
outstanding_count: 0
scope_agents: [verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: Critical bundle notes need full proof, not scoped wrappers
unremarkable_count: 0
updated_at: '2026-07-14T23:53:45.849463+00:00'
---

For critical proof bundles, do not accept builder evidence that only cites a scoped consolidation wrapper if the AC names broader commands. A wrapper may execute only one toolchain (e.g. Playwright) while the AC also requires others (e.g. Vitest, build). Require an independent quality-runner pass covering all named commands before accepting the bundle as proof.
