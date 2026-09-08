---
approved_at: null
categories: [domain-knowledge, pitfall]
confidence: 0.85
contested_by_task: null
created_at: '2026-09-08T01:51:37.022020+00:00'
didnt_use_count: 0
id: 2fbbdd6f-1a65-4a80-bad9-f50b404d3ecd
outstanding_count: 0
scope_agents: [planner, planner-challenger, builder, build-reviewer]
score: 0.85
source_agent: designer-challenger
state: curated
title: State browser IP-literal authorization explicitly
unremarkable_count: 0
updated_at: '2026-09-08T03:04:42.180603+00:00'
---

For browser destination designs, `serve/browser-mcp/src/owlbear_browser_mcp/server.py::_check_ssrf` currently permits internal targets only for a non-IP hostname with exact allowlist approval; IP literals remain categorically blocked. When authorizing loopback/private/link-local destinations, specify hostname and IP-literal behavior separately, especially `127.0.0.1`, rather than assuming wildcard or hostname rules cover both.
