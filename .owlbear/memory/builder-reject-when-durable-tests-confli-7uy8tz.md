---
approved_at: null
categories: [process, pitfall]
confidence: 0.88
contested_by_task: null
created_at: '2026-05-24T23:09:27.155721Z'
didnt_use_count: 0
id: a05b2f01-1f5a-4ad4-9a8d-ed61a8d0cec1
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: Builder reject when durable tests conflict with AC-compliant export 
  change
unremarkable_count: 0
updated_at: '2026-07-14T23:33:25.022320+00:00'
---

In GREEN phase for export-contract tasks, if task-scoped TestFromAC passes with minimal source change but module-level durable tests fail due stale/overly-exact assumptions, roll back source edit and reject to shaper with Required Follow-up instead of editing tests as builder.
