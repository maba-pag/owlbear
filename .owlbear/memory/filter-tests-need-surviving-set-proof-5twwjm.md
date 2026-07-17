---
approved_at: '2026-05-17T00:08:35.372007Z'
categories: [pitfall, process]
confidence: 0.88
contested_by_task: null
created_at: '2026-05-15T04:57:00.111871Z'
didnt_use_count: 2
id: 439e6179-6f0b-49c6-8cc4-8e3fa3960328
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.87
source_agent: reviewer
state: approved
title: Filter tests need surviving-set proof
unremarkable_count: 1
updated_at: '2026-07-17T06:28:15.013005+00:00'
---

For filter workflow tests, do not accept assertions that only prove some non-matching items disappear. Require proof of the surviving match set or exact count update after search, tag, priority, blocked, or clear actions; otherwise partial-filter and over-filter bugs can pass green.
