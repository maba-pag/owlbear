---
approved_at: null
categories: [pitfall, tool-usage]
confidence: 0.83
contested_by_task: null
created_at: '2026-05-17T04:26:24.525382Z'
didnt_use_count: 0
id: f87b6170-2e0c-4c39-aef7-e47e1dfcbaf5
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: builder
state: deleted
title: Regex-based CSS tests depend on line/indent formatting
unremarkable_count: 0
updated_at: '2026-07-14T23:57:04.705333+00:00'
---

For Cockpit CSS contract tests using extractSelectorBlock and /transition:.*/ patterns, multiline transition declarations or indented selectors inside media blocks can fail tests even when semantics are correct. Keep targeted declarations single-line and selector lines unindented when tests parse raw CSS text.
