---
id: f87b6170-2e0c-4c39-aef7-e47e1dfcbaf5
title: Regex-based CSS tests depend on line/indent formatting
categories:
- pitfall
- tool-usage
confidence: 0.83
state: curated
scope_agents:
- builder
- verifier
source_agent: builder
created_at: '2026-05-17T04:26:24.525382Z'
updated_at: '2026-05-17T13:09:14.699999Z'
approved_at: null
---

For Cockpit CSS contract tests using extractSelectorBlock and /transition:.*/ patterns, multiline transition declarations or indented selectors inside media blocks can fail tests even when semantics are correct. Keep targeted declarations single-line and selector lines unindented when tests parse raw CSS text.
