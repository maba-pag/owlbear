---
approved_at: '2026-05-15T19:50:51.044051Z'
categories: [pitfall, process]
confidence: 0.85
contested_by_task: null
created_at: '2026-05-13T20:58:18.680989Z'
didnt_use_count: 2
id: 7ed37efb-c5f6-416d-80f4-eaeeab527f48
outstanding_count: 0
scope_agents: [verifier, builder, shaper]
score: 0.85
source_agent: reviewer
state: approved
title: Pairwise precedence tests need positive reachability checks
unremarkable_count: 0
updated_at: '2026-07-17T06:28:15.058524+00:00'
---

For ordered-state helpers, adjacent pairwise precedence tests alone can miss an intermediate state that is only returned under an extra hidden condition. Require at least one direct positive assertion for each emitted state, not just competition cases.
