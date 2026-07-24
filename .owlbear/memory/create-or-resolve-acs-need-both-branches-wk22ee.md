---
approved_at: '2026-05-15T21:14:45.101673Z'
categories: [pitfall, process, domain-knowledge]
confidence: 0.94
contested_by_task: null
created_at: '2026-05-15T03:15:12.674835Z'
didnt_use_count: 54
id: bfe44264-fdb8-4f55-9d94-6e2543e88520
outstanding_count: 0
scope_agents: [verifier, shaper, builder]
score: 0.82
source_agent: reviewer
state: approved
title: Create-or-resolve ACs need both branches proved
unremarkable_count: 12
updated_at: '2026-07-24T19:45:01.628557+00:00'
---

When an AC says persistence must link to a created or resolved row, do not accept tests that only cover the create path from an empty DB. Require a seeded existing-row case, especially with conflicting scope/tenant keys, or URL-only/source-only resolution regressions can false-green.
