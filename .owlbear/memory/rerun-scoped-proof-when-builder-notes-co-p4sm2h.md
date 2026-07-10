---
id: 93de4aca-3a2b-4a5d-b206-bd193f561d9d
title: Rerun scoped proof when builder notes conflict
categories:
- process
- tool-usage
confidence: 0.8
state: curated
scope_agents:
- verifier
source_agent: reviewer
created_at: '2026-05-17T12:41:49.670267Z'
updated_at: '2026-05-17T13:09:22.487545Z'
approved_at: null
---

For behavioral Cockpit reviews, if builder evidence has contradictory test counts or only partial durable-proof notes, rerun the task-scoped and durable unit surfaces with quality-runner before PASS. It closes auditability gaps without escalating to a full-suite rerun by default.
