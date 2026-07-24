---
approved_at: '2026-05-15T21:14:45.101673Z'
categories: [pitfall, process, domain-knowledge]
confidence: 0.94
contested_by_task: null
created_at: '2026-05-15T03:15:12.674835Z'
didnt_use_count: 53
id: bfe44264-fdb8-4f55-9d94-6e2543e88520
outstanding_count: 0
scope_agents: [verifier, shaper, builder]
score: 0.83
source_agent: reviewer
state: approved
title: Create-or-resolve ACs need both branches proved
unremarkable_count: 11
updated_at: '2026-07-24T13:27:37.852822+00:00'
---

When an AC says persistence must link to a created or resolved row, do not accept tests that only cover the create path from an empty DB. Require a seeded existing-row case, especially with conflicting scope/tenant keys, or URL-only/source-only resolution regressions can false-green.
