---
approved_at: null
categories: [pitfall, process]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:36:52.142915Z'
didnt_use_count: 0
id: 29daadae-79b4-4a98-8764-10a926a8825f
outstanding_count: 0
scope_agents: [shaper, planner, verifier, builder]
score: 0.0
source_agent: copilot
state: deleted
title: Widely consumed API refactors need regression gates
unremarkable_count: 0
updated_at: '2026-07-14T23:48:46.037643+00:00'
---

For refactor tasks that change a widely consumed API, acceptance criteria should include a full-suite or domain-wide regression gate and name the suites or consumers that must be updated. Scoped green evidence can miss broad breakage across old call sites.
