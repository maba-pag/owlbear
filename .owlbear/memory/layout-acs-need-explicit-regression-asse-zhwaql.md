---
approved_at: null
categories: [pitfall, process]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-19T19:56:41.750382Z'
didnt_use_count: 0
id: 208b9edb-8bd7-4e6d-bcbb-72caf506d4d3
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: reviewer
state: deleted
title: Layout ACs need explicit regression assertions
unremarkable_count: 0
updated_at: '2026-07-14T23:53:46.143754+00:00'
---

When a Cockpit AC names specific layout behavior like full-width or single-column, do not PASS on source evidence plus generic sibling/gap tests. Require at least one discriminating assertion that would fail if width or direction changed; otherwise route to todo as a test-proof gap, not in-progress as an implementation defect.
