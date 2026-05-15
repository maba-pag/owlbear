---
id: 439e6179-6f0b-49c6-8cc4-8e3fa3960328
title: Filter workflow one-sided assertions false-green
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.92
state: curated
scope_agents:
- reviewer
- test-writer
source_agent: reviewer
created_at: '2026-05-15T04:57:00.111871Z'
updated_at: '2026-05-15T06:23:28.233020Z'
approved_at: null
---

In Cockpit filter reviews, reject E2E tests that only assert some non-matching cards disappear after a filter action. For search/priority/tags/blocked/clear flows, require proof of the surviving match set or exact count update; otherwise partial-filter and over-filter bugs can pass green.
