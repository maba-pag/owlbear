---
id: 6c709386-4ea3-4841-af76-ec1dd5afde6d
title: 'Builder: fail/escalate tracker tasks when child dependencies are not done'
categories:
- process
- pitfall
confidence: 0.91
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-12T13:37:52.885674Z'
updated_at: '2026-05-12T21:24:29.395211Z'
approved_at: null
---

For parent/tracker tasks with proof bundle skip and AC tied to child completion, builder must release with fail/escalation immediately when any required dependency is not in done state. Do not attempt implementation work. Re-dispatch only after all blocking children are complete.
