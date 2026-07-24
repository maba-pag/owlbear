---
approved_at: '2026-05-15T20:44:03.204670Z'
categories: [process, pitfall, domain-knowledge]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-14T00:11:42.481756Z'
didnt_use_count: 65
id: 2b7191bd-c225-4fcb-be78-15b1b780c3fb
outstanding_count: 1
scope_agents: [verifier, shaper, builder]
score: 0.84
source_agent: reviewer
state: approved
title: Cross-check refined RED test AC against paired implementation task
unremarkable_count: 16
updated_at: '2026-07-24T19:45:01.661206+00:00'
---

For RED test-task reviews, compare architect-refined AC with the paired implementation task and parent brief. A refined test AC can over-constrain implementation semantics or omit one half of a toggle contract even when the builder executes it correctly; route these as backlog-level contract defects, especially on re-review cycles.
