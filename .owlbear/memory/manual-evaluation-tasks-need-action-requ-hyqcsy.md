---
id: 84a26082-d22f-4eb5-894d-e46d342b64df
title: Manual evaluation tasks need action requests
categories:
- pitfall
- process
confidence: 0.82
state: curated
scope_agents:
- verifier
- collector
source_agent: copilot
created_at: '2026-05-17T01:38:11.346418Z'
updated_at: '2026-05-17T01:48:31.794572Z'
approved_at: null
---

When a task requires human execution or judgment and the body has only pipeline pass-through notes, treat it as a missing-evidence block. Create an action/decision request with the exact checklist, then block/release the task instead of calling it an implementation failure.
