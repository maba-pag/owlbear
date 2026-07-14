---
approved_at: null
categories: [process, tool-usage]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-17T12:41:49.670267Z'
didnt_use_count: 0
id: 93de4aca-3a2b-4a5d-b206-bd193f561d9d
outstanding_count: 0
scope_agents: [verifier]
score: 0.0
source_agent: reviewer
state: deleted
title: Rerun scoped proof when builder notes conflict
unremarkable_count: 0
updated_at: '2026-07-14T23:52:41.465178+00:00'
---

For behavioral Cockpit reviews, if builder evidence has contradictory test counts or only partial durable-proof notes, rerun the task-scoped and durable unit surfaces with quality-runner before PASS. It closes auditability gaps without escalating to a full-suite rerun by default.
