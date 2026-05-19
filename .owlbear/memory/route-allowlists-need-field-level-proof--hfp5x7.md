---
id: 05d14bba-d6cb-4a42-80a9-29c2a8079291
title: Route allowlists need field-level proof across the full proof surface
categories:
- pitfall
- process
confidence: 0.89
state: curated
scope_agents:
- reviewer
- test-writer
source_agent: reviewer
created_at: '2026-05-19T04:23:37.421682Z'
updated_at: '2026-05-19T10:43:13.608629Z'
approved_at: null
---

When reviewing API route tasks that mock their engine dependency, include adjacent durable engine tests in the proof surface before flagging missing semantics. But if an AC names multiple editable fields, require executable proof for each field or for a generic update loop; a status-only route test that sends all fields can false-green if some fields are silently dropped.
