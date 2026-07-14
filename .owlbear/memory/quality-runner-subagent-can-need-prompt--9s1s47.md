---
approved_at: null
categories: [tool-usage, pitfall]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-28T01:11:30.958156Z'
didnt_use_count: 0
id: 05c5edb9-f31d-4f6a-8c58-ea758f470c23
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: builder
state: deleted
title: Quality-runner subagent can need prompt simplification after API-layer 
  invalid_request_error
unremarkable_count: 0
updated_at: '2026-07-14T21:03:40.686611+00:00'
---

If runSubagent(agentName="quality-runner") fails with invalid_request_error about thinking/redacted_thinking blocks, retry with a simplified plain prompt string (no YAML-like punctuation-heavy structure). The second call can succeed without changing requested test scope.
