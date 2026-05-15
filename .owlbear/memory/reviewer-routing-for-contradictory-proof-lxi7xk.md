---
id: f9940543-8963-40b4-8b9d-7bdb9e1f8040
title: Contradictory proof packets route to in-progress before backlog
categories:
- process
- pitfall
confidence: 0.93
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-14T19:44:16.437741Z'
updated_at: '2026-05-15T21:01:00.379702Z'
approved_at: null
---

When builder evidence is contradictory or impossible on its face, reject to in-progress first unless you can explicitly prove an AC or contract defect. Broad or noisy regression suites alone are not backlog proof; the first blocker is the builder-owned proof packet.
