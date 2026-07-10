---
id: a05b2f01-1f5a-4ad4-9a8d-ed61a8d0cec1
title: Builder reject when durable tests conflict with AC-compliant export change
categories:
- process
- pitfall
confidence: 0.88
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-24T23:09:27.155721Z'
updated_at: '2026-05-25T00:10:28.800055Z'
approved_at: null
---

In GREEN phase for export-contract tasks, if task-scoped TestFromAC passes with minimal source change but module-level durable tests fail due stale/overly-exact assumptions, roll back source edit and reject to shaper with Required Follow-up instead of editing tests as builder.
