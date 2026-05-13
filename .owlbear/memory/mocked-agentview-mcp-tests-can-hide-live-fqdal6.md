---
id: 2aed1c0e-7af4-4f92-988d-06d68112b97f
title: Mocked AgentView MCP tests can hide live signature drift
categories:
- pitfall
- process
- tool-usage
confidence: 0.88
state: curated
scope_agents:
- reviewer
- architect
- test-writer
- builder
source_agent: reviewer
created_at: '2026-05-13T08:16:00.904001Z'
updated_at: '2026-05-13T08:39:28.779155Z'
approved_at: null
---

When MCP adapter tests replace engine._agent_view with a MagicMock, they only prove handler-to-mock kwarg translation. If AC depends on live MCP -> AgentView -> engine delivery, reviewers should inspect AgentView signatures or require real-AppContext handler tests; otherwise unexpected-kwarg TypeErrors can ship behind passing tests.
