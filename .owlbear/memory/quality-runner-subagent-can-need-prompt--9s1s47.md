---
id: 05c5edb9-f31d-4f6a-8c58-ea758f470c23
title: Quality-runner subagent can need prompt simplification after API-layer invalid_request_error
categories:
- tool-usage
- pitfall
confidence: 0.82
state: curated
scope_agents:
- builder
- verifier
source_agent: builder
created_at: '2026-05-28T01:11:30.958156Z'
updated_at: '2026-05-28T01:31:47.135442Z'
approved_at: null
---

If runSubagent(agentName="quality-runner") fails with invalid_request_error about thinking/redacted_thinking blocks, retry with a simplified plain prompt string (no YAML-like punctuation-heavy structure). The second call can succeed without changing requested test scope.
