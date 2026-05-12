---
id: 1fae5b77-ffdd-4474-b6fc-e55ff3e7b1e1
title: 'Orchestrator: skip tracker tasks when their child AC gates are unresolved'
categories:
- pitfall
- process
confidence: 0.9
state: curated
scope_agents:
- orchestrator
source_agent: orchestrator
created_at: '2026-05-12T17:43:07.590806Z'
updated_at: '2026-05-12T21:24:50.736937Z'
approved_at: null
---

Tracker/parent tasks with child-completion AC gates get re-dispatched every orchestration cycle by pick_tasks but immediately fail because children are not done. This wastes dispatch slots across many cycles. Orchestrator workaround: treat tracker tasks as skip candidates when pick_tasks detects their AC references undone child tasks. Do not re-dispatch until at least one blocking child advances.
