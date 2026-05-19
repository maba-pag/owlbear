---
id: 208b9edb-8bd7-4e6d-bcbb-72caf506d4d3
title: Layout ACs need explicit regression assertions
categories:
- pitfall
- process
confidence: 0.86
state: pending
scope_agents:
- reviewer
- test-writer
source_agent: reviewer
created_at: '2026-05-19T19:56:41.750382Z'
updated_at: '2026-05-19T19:56:41.750382Z'
approved_at: null
---

When a Cockpit AC names specific layout behavior like full-width or single-column, do not PASS on source evidence plus generic sibling/gap tests. Require at least one discriminating assertion that would fail if width or direction changed; otherwise route to todo as a test-proof gap, not in-progress as an implementation defect.
