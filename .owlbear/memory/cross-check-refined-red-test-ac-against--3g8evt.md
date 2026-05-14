---
id: 2b7191bd-c225-4fcb-be78-15b1b780c3fb
title: Cross-check refined RED test AC against paired implementation task
categories:
- process
- pitfall
- domain-knowledge
confidence: 0.9
state: curated
scope_agents:
- reviewer
- architect
- test-writer
source_agent: reviewer
created_at: '2026-05-14T00:11:42.481756Z'
updated_at: '2026-05-14T03:03:19.840384Z'
approved_at: null
---

For RED test-task reviews, compare architect-refined AC with the paired implementation task and parent brief. A refined test AC can over-constrain implementation semantics or omit one half of a toggle contract even when the builder executes it correctly; route these as backlog-level contract defects, especially on re-review cycles.
