---
id: 6f72dc3f-ba2a-4c73-929e-d0cb8852c83f
title: quality-runner full mode timeout fallback
categories:
- tool-usage
- env-context
confidence: 0.8
state: curated
scope_agents:
- builder
- verifier
source_agent: builder
created_at: '2026-05-27T20:46:53.600484Z'
updated_at: '2026-05-27T22:49:36.971805Z'
approved_at: null
---

For task-level smoke work touching mcp-knowledge server, quality-runner mode=full can time out on tests/ serve/ -m "not api" and auto-fallback to scoped evidence. Plan scoped proof runs (task tests + relevant regression file) as primary evidence and treat full-mode as best-effort.
