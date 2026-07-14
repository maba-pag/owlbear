---
approved_at: null
categories: [env-context, pitfall]
confidence: 0.95
contested_by_task: null
created_at: '2026-05-17T13:33:37.452313Z'
didnt_use_count: 0
id: 19be6463-6c27-410e-a59d-72c97e015152
outstanding_count: 0
scope_agents: [builder, shaper, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: ob-knowledge MCP server now uses owlbear-dev (dev branch)
unremarkable_count: 0
updated_at: '2026-07-14T23:52:41.593058+00:00'
---

The ob-knowledge MCP server was reconfigured to use `--project ../owlbear-dev` instead of `--project ../owlbear`. Implications:\n1. Code changes committed to owlbear-dev (dev branch) are immediately available after MCP server restart\n2. NEVER modify files directly in /Users/markus/Projects/owlbear/ (main branch) — all changes go to owlbear-dev\n3. The main branch at ../owlbear is synced FROM dev via a workflow — never commit directly there\n4. Other MCP servers (kanban, memory, browser) may still point to ../owlbear — only knowledge was changed
