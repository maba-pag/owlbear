---
id: 14a20984-6567-4e27-a03e-7efe9d1acd6c
title: Follow-up tasks need live board and source verification
categories:
- pitfall
- process
confidence: 0.84
state: curated
scope_agents:
- verifier
- planner
- collector
source_agent: copilot
created_at: '2026-05-17T01:38:42.937564Z'
updated_at: '2026-05-17T01:48:32.004421Z'
approved_at: null
---

When reviewing research roll-ups or spawned follow-ups, verify live source files and live board state directly. Parent prose claiming children are archived or blocked can drift; dispatch needs machine-readable metadata such as `blocked: true` and correct `depends_on`, not just text.
