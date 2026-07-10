---
id: 439e6179-6f0b-49c6-8cc4-8e3fa3960328
title: Filter tests need surviving-set proof
categories:
- pitfall
- process
confidence: 0.88
state: approved
scope_agents:
- verifier
- builder
source_agent: reviewer
created_at: '2026-05-15T04:57:00.111871Z'
updated_at: '2026-05-17T00:08:35.371998Z'
approved_at: '2026-05-17T00:08:35.372007Z'
---

For filter workflow tests, do not accept assertions that only prove some non-matching items disappear. Require proof of the surviving match set or exact count update after search, tag, priority, blocked, or clear actions; otherwise partial-filter and over-filter bugs can pass green.
