---
id: 19be6463-6c27-410e-a59d-72c97e015152
title: ob-knowledge MCP server now uses owlbear-dev (dev branch)
categories:
- env-context
- pitfall
confidence: 0.95
state: curated
scope_agents:
- builder
- researcher
- reviewer
source_agent: copilot
created_at: '2026-05-17T13:33:37.452313Z'
updated_at: '2026-05-17T17:03:12.394828Z'
approved_at: null
---

The ob-knowledge MCP server was reconfigured to use `--project ../owlbear-dev` instead of `--project ../owlbear`. Implications:\n1. Code changes committed to owlbear-dev (dev branch) are immediately available after MCP server restart\n2. NEVER modify files directly in /Users/markus/Projects/owlbear/ (main branch) — all changes go to owlbear-dev\n3. The main branch at ../owlbear is synced FROM dev via a workflow — never commit directly there\n4. Other MCP servers (kanban, memory, browser) may still point to ../owlbear — only knowledge was changed
